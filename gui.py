from tkinter import *
import threading
import nltk
from nltk.tag import map_tag  # to simplify part-of-speech tagging
import text_processor


class GUI(threading.Thread):
    def __init__(self, PL, T, D, TranscriptDuration):
        super().__init__()
        self.PL = PL  # playlist
        self.T = T  # transcriber
        self.D = D  # dictionary
        self.TranscriptDuration = TranscriptDuration
        self.root = Tk()
        self.track_list = Listbox(self.root, selectmode=SINGLE)  # visual representation of playlist
        self.track_list.grid(row=0, rowspan=2)
        for item in PL.entry_list:
            self.track_list.insert(END, item.audio_path)
        self.track_list.selection_set(0)
        self.track_list.activate(0)
        self.prev_button = Button(self.root, text='Prev')
        self.prev_button.grid(row=0, column=1)
        # prev_button.pack(side=LEFT, fill=X)

        self.play_button = Button(self.root, text='Play')
        # play_button.pack(side=LEFT, fill=X)
        self.play_button.grid(row=0, column=2)

        self.stop_button = Button(self.root, text='Stop')
        self.stop_button.grid(row=0, column=3)
        # stop_button.pack(side=LEFT, fill=X)

        self.next_button = Button(self.root, text='Next')
        self.next_button.grid(row=0, column=4)
        # next_button.pack(side=LEFT, fill=X)

        self.pause_button = Button(self.root, text='Pause')
        self.pause_button.grid(row=0, column=5)
        # pause_button.pack(side=BOTTOM, fill=X)

        self.transcribe_button = Button(self.root, text='Transcribe')
        self.transcribe_button.grid(row=1, column=1)
        # transcribe_button.pack(side=LEFT, fill=X)

        self.get_pos_button = Button(self.root, text='Get_Pos')
        self.get_pos_button.grid(row=1, column=2)
        # get_pos_button.pack(side=LEFT, fill=X)

        self.go_to_button = Button(self.root, text='Go_to(time in sec)')
        self.go_to_button.grid(row=1, column=3)
        # go_to_button.pack(side=LEFT, fill=X)

        self.target_time_entry = Entry(self.root)
        self.target_time_entry.grid(row=1, column=4, columnspan=2)

        self.dialogue_box = Text(self.root, wrap=WORD, height=7)
        self.dialogue_box.configure(font=("Times New Roman", 14))
        self.dialogue_box.grid(row=3, columnspan=5)

        self.transcription_box = Text(self.root, wrap=WORD, height=15)
        self.transcription_box.configure(font=("Times New Roman", 14))
        self.transcription_box.grid(row=4, columnspan=5)
        self.transcription_scrollbar = Scrollbar(self.root, orient="vertical", command=self.transcription_box.yview)
        self.transcription_box.configure(yscrollcommand=self.transcription_scrollbar.set)
        self.transcription_scrollbar.grid(row=4, column=6)

        self.show_recent_words_button = Button(self.root, text='Show Recent Words')
        self.show_recent_words_button.grid(row=2, column=3)

        self.speak_button = Button(self.root, text='Voice Command')
        self.speak_button.grid(row=2, column=2)

        self.play_button.bind("<Button-1>", self.play_track)
        self.stop_button.bind("<Button-1>", self.stop_track)
        self.next_button.bind("<Button-1>", self.next_track)
        self.prev_button.bind("<Button-1>", self.prev_track)
        self.pause_button.bind("<Button-1>", self.pause_track)
        self.transcribe_button.bind("<Button-1>", self.transcribe_recent)
        self.get_pos_button.bind("<Button-1>", self.get_pos)
        self.go_to_button.bind("<Button-1>", self.go_to)
        self.speak_button.bind("<Button-1>", self.parse_voice)
        self.show_recent_words_button.bind("<Button-1>", self.show_recent_words)

        # making sure that first utterance shows up:
        self.cur_interval_start = -0.001
        self.cur_interval_end = 0

        self.root.after(50, self.update_script)

        # self.root.mainloop()
    def play_track(self, event=None):
        is_unpausing = self.PL.play()
        if is_unpausing is True:
            self.skip_update = True

    def stop_track(self, event):
        self.PL.stop()

    def prev_track(self, event):
        self.PL.goto_prev()
        self.track_list.selection_clear(0, END)
        self.track_list.selection_set(self.PL.curr_index)
        self.track_list.activate(self.PL.curr_index)

    def next_track(self, event):
        self.PL.goto_next()
        self.track_list.selection_clear(0, END)
        self.track_list.selection_set(self.PL.curr_index)
        self.track_list.activate(self.PL.curr_index)

    def pause_track(self, event=None):
        self.PL.pause()

    def transcribe_recent(self, event):
        offset = max(0, self.PL.current_time() - self.TranscriptDuration)
        transcription = self.T.transcribe_audio(self.PL.get_cur_track_path(), self.TranscriptDuration, offset)
        self.dialogue_box.insert(0.2, transcription + "\n\n")

    def parse_voice(self, event=None):
        while True:
            self.dialogue_box.insert(0.2, "Speech Recognizer: Listening ...\n\n")
            transcription = self.T.transcribe_mic()
            if transcription!='inaudible':
                break
            else:
                self.dialogue_box.insert(0.2, "Speech Recognizer: I didn't get it, please try again\n\n")
        self.dialogue_box.insert(0.2, "User: {}\n\n".format(transcription))
        parsed_command = text_processor.parse_command(transcription)

        if parsed_command['func'] == 'play':
            self.play_track()
        elif parsed_command['func'] != 'unknown' and parsed_command['phrase'] == 'it':
            self.dialogue_box.insert(0.2, "assistant could not comprehend the target phrase\n\n")

        elif parsed_command['func'] == 'translate':
            recently_played_words = self.PL.get_recent_words()

            target_word = None
            max_len = 0
            for w in parsed_command['phrase']:
                if len(w) > max_len:
                    target_word = w
                    max_len = len(w)
            target_word = text_processor.find_most_similar_word(target_word, recently_played_words)

            translation_dict = self.D.translate(target_word, 'ru')
            translation = translation_dict['translatedText']
            self.dialogue_box.insert(0.2, "translation of {}: {}\n\n".
                                format(target_word, translation))

        elif parsed_command['func'] == 'define':
            recently_played_words = self.PL.get_recent_words()

            phrase = parsed_command['phrase']
            target_word = None
            max_len = 0
            for w in phrase:
                if len(w) > max_len:
                    target_word = w
                    max_len = len(w)
            target_word = text_processor.find_most_similar_word(target_word, recently_played_words)

            self.PL.get_word_context(target_word)

            definition = self.D.define(target_word)
            self.dialogue_box.insert(0.2, "definition of {}: {}\n\n".
                                format(target_word, definition))
            self.dialogue_box.insert(0.2, "context utterance: {}\n".format(context_utterance))
            utt_tokenized = nltk.word_tokenize(context_utterance)
            utt_tagged = nltk.pos_tag(utt_tokenized)
            simplifiedTags = [(word, map_tag('en-ptb', 'universal', tag)) for word, tag in utt_tagged]
            pos = 'UNKNOWN'
            for token, tag in simplifiedTags:
                if token == target_word:
                    self.dialogue_box.insert(0.2, 'POS of {} is: {}\n'.format(target_word, tag))
                    break

        print("parsed command: {}\n".format(parsed_command))

    # shows the most recent words from provided transcript
    def show_recent_words(self, event):
        recent_words = self.PL.get_recent_words()
        self.dialogue_box.insert(0.2, ' '.join(recent_words) + "\n\n")
        self.transcription_box.see("end")

    def get_pos(self, event):
        pos = self.PL.current_time()
        print(pos)

    def go_to(self, event):
        target_time = float(self.target_time_entry.get())
        self.PL.go_to(target_time)

    def update_script(self):
        t = max(self.PL.current_time(), 0)
        if t > self.cur_interval_end or t < self.cur_interval_start:
            # print("t: {}, cur_interval_start: {}, cur_interval_end: {}".
            #       format(t, cur_interval_start, cur_interval_end))
            # sys.stdout.flush()

            utterance = self.PL.get_utterance(t)
            self.cur_interval_start = utterance['start_time']
            self.cur_interval_end = utterance['end_time']
            self.transcription_box.insert('end', '{}\n\n'.format(utterance['text']))
            self.transcription_box.see('end')

        self.root.after(150, self.update_script)