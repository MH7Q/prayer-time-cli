import os
import pygame
import arabic_reshaper
from bidi.algorithm import get_display

ADHAN_FILE = "adhan.mp3"

def fix_text(text, lang):
    """Reshapes Arabic text so letters connect properly."""
    if lang == "ar":
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except:
            return text
    return text

def init_audio():
    try:
        pygame.mixer.init()
    except: pass

def play_adhan():
    if os.path.exists(ADHAN_FILE):
        try:
            if not pygame.mixer.get_init(): pygame.mixer.init()
            pygame.mixer.music.load(ADHAN_FILE)
            pygame.mixer.music.play()
            return True
        except: return False
    return False

def stop_audio():
    try:
        pygame.mixer.music.stop()
    except: pass

def is_audio_playing():
    try:
        return pygame.mixer.music.get_busy()
    except: return False