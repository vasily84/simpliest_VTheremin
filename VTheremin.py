import tkinter as tk
import threading
import pyaudio
from scipy.io.wavfile import write as write_wav
import numpy as np
import datetime

class CThereminAudio():
    """ implements Theremin audio synthesize and play """
    def __init__(self,timeStep=0.1):
        self.timeStep = timeStep
        self.FPS = 44100
        self.X,self.Y,self.Z,self.Freq,self.Volume = 0, 0, 0, 0, 0
        self.silent = False
        self.guitar = False
        self.distortion_all_volume = False
        self.distortion_high_volume = False
        self.new_wav()
        self._Terminated = False
        self.soundThread = threading.Thread(target=self._audio_loop)
        self.soundThread.start()
        
    def set_XY(self,X,Y):
        self.X,self.Y = X, Y

    def get_string(self):
        return ("Freq = "+"{:.2f}".format(self.Freq)+" [Hz] , Volume = "+str(int(self.Volume*100)))

    def _produce_sound(self,timeSpace):
        """ synthesize a sound fragment with the specified characteristics """
        CHUNK = int(self.FPS*self.timeStep)
        F = 110.+(880.-110)*self.X # freqency in Hz
        A = self.Y # Amplitude
        T = 1./F # period in seconds
        tT = self.timeStep / T # float number of waves on timeStep
        chunkInt = round((CHUNK)*int(tT)/tT) # end index of last integer wave
        timeSpace = timeSpace[:chunkInt-1]
        self.Freq = F
        self.Volume = A
        sound_signal = A*np.sin(2*np.pi*F*(timeSpace)) # base sound signal

        if self.guitar == True:
            guitar_overtones = A*0.5*np.sin(2*np.pi*F*2*(timeSpace)) + \
            A*0.25*np.sin(2*np.pi*F*4*(timeSpace))
            sound_signal = sound_signal+guitar_overtones

        Amax = np.max(sound_signal)
        sound_signal = (self.Volume/Amax)*sound_signal
            
        if self.distortion_high_volume == True:
            sound_signal = np.clip(sound_signal,-0.7,0.7)

        if self.distortion_all_volume == True:
            sound_signal = np.clip(sound_signal,-0.7*self.Volume,0.7*self.Volume)

        if self.silent == True:
            audio_buf = 0.*timeSpace   
        else:
            audio_buf = sound_signal
        return audio_buf
        

    def _audio_loop(self):
        """ loop function for audio thread """
        # init output audio device
        CHUNK = int(self.FPS*self.timeStep)
        
        audio = pyaudio.PyAudio()
        audio_stream = audio.open(format=pyaudio.paFloat32, channels=1, rate=self.FPS, output=True)

        timeSpace = np.linspace(0,self.timeStep,CHUNK,dtype=np.float32)
    
        while not self._Terminated:
            audio_buf = self._produce_sound(timeSpace)
            audio_stream.write(audio_buf.astype(np.float32).tobytes())
            self.audio_frames.append(np.copy(audio_buf))

        # release audio device
        audio_stream.stop_stream()
        audio_stream.close()
        audio.terminate()

    def Terminate(self):
        self._Terminated = True
        self.soundThread.join()

    def save_wav(self):
        fileName = 'play_{date:%Y_%m_%d_%H_%M_%S}.wav'.format(date=datetime.datetime.now())
        write_wav(fileName,self.FPS,np.block(self.audio_frames))

    def new_wav(self):
        self.audio_frames = []
    

class CApplication():
    """ implements GUI for Theremin control """
    def __init__(self, Theremin):
        self.Theremin = Theremin
        self.window = tk.Tk()
        self.window.title("VTheremin")
        self.window.geometry("640x480")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close_window)
        self.window.bind_all("<KeyPress>", self._on_key_press)
        self.window.bind_all("<Motion>",self._on_mouse_move)
        tk.Label(self.window,justify=tk.CENTER, text="F5 : silent mode, F6 : guitar overtones, F7 : distortion all volume scale, F8 : distortion at hight volume").pack(side=tk.TOP)
        self.lbl_mode = tk.Label(self.window,font='Times 18', text="")  
        self.lbl_mode.pack(side=tk.TOP)
        self.lbl_FV = tk.Label(self.window, justify = tk.CENTER,font='Times 18', text="")  
        self.lbl_FV.pack(side=tk.TOP)
        self.window.mainloop()
        
    def _on_close_window(self):
        self.Theremin.save_wav()
        self.Theremin.Terminate()
        self.window.destroy()
    
    def _on_mouse_move(self,mouseEvent):
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        self.Theremin.set_XY(mouseEvent.x/w,1.-mouseEvent.y/h)
        self.lbl_FV.config(text=self.Theremin.get_string())

    def _on_key_press(self,keyEvent):
        if keyEvent.keycode == 116: # silent mode
            self.Theremin.silent = not self.Theremin.silent
        if keyEvent.keycode == 117: # guitar mode
            self.Theremin.guitar = not self.Theremin.guitar 
        if keyEvent.keycode == 118: # distortion all scale
            self.Theremin.distortion_all_volume = not self.Theremin.distortion_all_volume
        if keyEvent.keycode == 119: # distortion high Volume
                self.Theremin.distortion_high_volume = not self.Theremin.distortion_high_volume
        
        stateDict = []
        if self.Theremin.silent:
            stateDict.append('silent')
        if self.Theremin.guitar:
            stateDict.append('guitar')
        if self.Theremin.distortion_all_volume:
            stateDict.append('distortion F7')
        if self.Theremin.distortion_high_volume:
            stateDict.append('distortion F8')
        self.lbl_mode.config(text=str(stateDict))
        
def main():
    Theremin = CThereminAudio()
    _ = CApplication(Theremin)
    
if __name__=='__main__':
    main()