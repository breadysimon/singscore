import codecs
from pydub import AudioSegment
from pydub.playback import play
from collections import namedtuple
import csv

Node = namedtuple(
    "Node", "tenuto eot staccato eos sharp flat octave_up octave_down natural")
Key = namedtuple("Key", "notes sharp, flat")

SAMPLES = {}
with open("samples.csv") as f:
    data = csv.reader(f)
    for row in data:
        SAMPLES[row[0]] = Node(
            int(row[1]), int(row[2]),
            int(row[3]), int(row[4]),
            row[5], row[6],
            row[7], row[8],
            row[9]
        )

KEYS = {
    "A": Key(["di", "re", "mi", "fi", "si", "la", "ti"], "C", "Bb"),
    "Bb": Key(["do", "re", "me", "fa", "so", "la", "te"], "B", "A"),
    "B": Key(["di", "ri", "mi", "fi", "si", "li", "ti"], "C", "Bb"),
    "C": Key(["do", "re", "mi", "fa", "so", "la", "ti"], "C#", "B"),
    "C#": Key(["di", "ri", "fa", "fi", "si", "li", "do1"], "D", "C"),
    "c": Key(["do", "re", "me", "fa", "so", "le", "te"], "C#", "B"),
    "Db": Key(["do", "ra", "me", "fa", "se", "le", "te"], "D", "C#"),
    "D": Key(["di", "re", "mi", "fi", "so", "la", "ti"], "C#", "D#"),
    "Eb": Key(["do", "re", "me", "fa", "so", "le", "te"], "F", "D#"),
    "E": Key(["di", "ri", "mi", "fi", "si", "la", "ti"], "F", "D#"),
    "F": Key(["do", "re", "mi", "fa", "so", "la", "te"], "F#", "E"),
    "F#": Key(["di", "ri", "mi", "fi", "si", "li", "do1"], "Gb", "F"),
    "Gb": Key(["ti1-", "ra", "me", "fa", "se", "le", "te"], "F", "G"),
    "G": Key(["do", "re", "mi", "fi", "so", "la", "ti"], "G#", "F#"),
}


def parse(key, tempo, xx):
    s = None
    duration = parse_duration(tempo, xx)
    is_staccato = (parse_note_type(xx) == 'staccato')

    for x in xx.split(','):
        note = parse_note(key, x)
        ss = get_sound(key, note, is_staccato, duration)
        if s is None:
            s = ss
        else:
            s = s.overlay(ss)
    return s


def parse_note_type(x):
    if '!' in x:
        return 'staccato'
    return 'tenuto'


def octave_shift(x, note):
    for i in range(x.count('^')):
        note = SAMPLES[note].octave_up

    for i in range(x.count('v')):
        note = SAMPLES[note].octave_down

    return note


def parse_note(key, x):
    n = int(x[0])-1
    if n < 0:
        note = "rest"
    else:
        note = KEYS[key].notes[n]

    if 'v' in x or '^' in x:
        note = octave_shift(x, note)

    if '#' in x:
        for i in range(x.count('#')):
            note = SAMPLES[note].sharp

    if 'b' in x:
        for i in range(x.count('b')):
            note = SAMPLES[note].flat

    if '$' in x:
        note = SAMPLES[note].natural

    print('note:', note)
    return note


def parse_duration(tempo, x):
    beat = int(60000//tempo)
    l = beat

    ext = x.count('-')
    l = l + l * ext

    dec = x.count('_')
    l = l / (2 ** dec)

    if '.' in x:
        l = l * 2 * (1 - 0.5**(1+x.count('.')))

    print('duration:', l)
    return l


sound = AudioSegment.from_wav("\\samples.wav")


def get_sound(key, note, staccato, duration):
    nn = SAMPLES[note]
    pos = nn.tenuto
    end_pos = nn.eot
    if staccato:
        pos = nn.staccato
        end_pos = nn.eos

    print("position:", pos)

    e = pos+duration
    if e > end_pos:
        snd = sound[pos:end_pos]
        rest_pos = SAMPLES['rest'].tenuto
        for i in range(int(e - end_pos)//1000):
            snd = snd + sound[rest_pos:rest_pos+1000]
        snd = snd + sound[rest_pos:rest_pos+(e-end_pos) % 1000]
        return snd
    else:
        return sound[pos:e]


def merge(tracks, track):
    if track:
        if tracks:
            tracks = tracks.overlay(track-10)
        else:
            tracks = track
    return tracks


def link(all, sec):
    if sec:
        if all:
            all = all+sec
        else:
            all = sec
    return all


def compose(key, tempo, score, tn=0):
    all = None
    for z in score.split(';'):
        z=z.strip()
        if z.startswith('key='):
            key = z[4:]
            continue
        tracks = None
        n = 0
        for y in z.split('|'):
            n = n+1
            if tn == 0 or tn == n:
                track = None
                for x in y.split(' '):
                    if x.strip() != '':
                        t = parse(key, tempo, x)
                        track = link(track, t)
                tracks = merge(tracks, track)
        all = link(all, tracks)
    return all


def sing(key, tempo, score, tn=0):
    song = compose(key, tempo, score, tn=tn)
    play(song)


def export(key, tempo, score, filename, tn=0):
    song = compose(key, tempo, score, tn=tn)
    song.export(filename+".mp3", format="mp3")


class song:
    def __init__(self, file):
        with codecs.open(file+".sco", "r", "utf-8") as f:
            self.title = f.readline()
            info = f.readline()
            self.key, tmp = info.split(' ')
            self.tempo = int(tmp.strip("\n"))
            self.score = ""
            while True:
                l = f.readline()
                if l == "":
                    break
                if l.startswith('#'):
                    continue
                self.score = self.score+";"+l.strip('\n;\r\t ')

    def sing(self, tn=0):
        sing(self.key, self.tempo, self.score, tn=tn)

    def export(self, filename, tn=0):
        export(self.key, self.tempo, self.score,filename, tn=tn)


def test():
    nn = 'fa1- fi1- so1- si1- la1- li1- ti1- do di re ri mi fa fi so si la li ti'
    # nn='do1 di1 re1 ri1 mi1 fa1 fi1 so1 si1 la1 li1 ti1 do2'
    # nn='fa1- so1- la1- ti1- do re mi fa so la ti do1 re1 mi1 fa1 so1 la1 ti1 do2 re2 mi2'
    # nn='do1 ti te la le so se fa mi me re ra do ti1- te1- la1- le1- so1- se1- fa1-'
    s = sound[:10]
    for x in nn.split(' '):
        s = s+get_sound('C', x, False, 500)
    play(s)


def test1():
    sing("C", 60, "1,3,5 4,6,1^")


def test2():
    sing('C', 120, '1^ 2^ 3^-|5v---; 3 6 3|6v---')


def test3():
    sing('C', 60, '1 1. 1_')
