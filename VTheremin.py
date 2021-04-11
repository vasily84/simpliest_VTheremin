import tkinter as tk
import threading
import pyaudio
from scipy.io.wavfile import write as write_wav
import numpy as np
import datetime

# 110->220->440->880
F_LOW = 110.
NOTES_COUNT = 36
F_HIGH = F_LOW*2**(NOTES_COUNT/12)


class CThereminAudio():
    """ implements Theremin audio synthesize and play """
    def __init__(self):
        self.frameTime = 0.1
        self.FPS = 44100
        self.phase0 = 0
        self.X,self.Y,self.Freq,self.Volume = 0, 0, 0, 0
        self.silent, self.guitar, self.accordion, self.distortion = False,False,False,False

        self.guitar_param, self.accordion_param, self.distortion_param = 0.5, 0.5, 0.5
        
        self.new_wav()
        self._Terminated = False
        self.soundThread = threading.Thread(target=self._audio_loop)
        self.soundThread.start()
        
    def set_XY(self,X,Y):
        self.X, self.Y = X, Y

    def get_string(self):
        return ("Freq = "+"{:.2f}".format(self.Freq)+" [Hz] , Volume = "+str(int(self.Volume*100))+" [%], dt = {:.2f}".format(self.frameTime)+" [sec]")

    def _produce_sound(self):
        dt = 1./self.FPS
        timeSpace = np.arange(start=dt,stop=self.frameTime,step=dt)
        F = F_LOW+(F_HIGH-F_LOW)*self.X # freqency in Hz 
        self.Freq = F
        A = np.linspace(self.Volume,self.Y,len(timeSpace))
        self.Volume = self.Y # Amplitude
        phaseSpace = 2*np.pi*F*(timeSpace)+self.phase0
        # запоминаем конечную фазу сигнала
        self.phase0 = 2*np.pi*F*(timeSpace[-1])+self.phase0
        sound_signal = A*np.sin(phaseSpace) # base sound signal
        
        if self.guitar: # добавляем удвоенную частоту - обертон
            signal2 = (A*self.guitar_param)*np.sin(2.*phaseSpace) 
            sound_signal = sound_signal+signal2

        if self.accordion: # добавляем близкую частоту для биения колебаний
            signal2 = (A*self.guitar_param)*np.sin(1.1*self.accordion_param*phaseSpace) 
            sound_signal = sound_signal+signal2

        
        if self.distortion: # дисторшн-эффект - обрезаем сигнал выше определенной амплитуды
            sound_signal = np.clip(sound_signal,-self.distortion_param,self.distortion_param)

        if self.silent: # "выключаем" звук
            audio_buf = np.zeros_like(timeSpace)   
        else:
            audio_buf = sound_signal

        return audio_buf
        

    def _audio_loop(self):
        """ loop function for audio thread """
        # init output audio device
        audio = pyaudio.PyAudio()
        audio_stream = audio.open(format=pyaudio.paFloat32, channels=1, rate=self.FPS, output=True)

        while not self._Terminated:
            audio_buf = self._produce_sound()
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
        self.window.bind_all("<MouseWheel>", self._on_mouse_wheel)
        tk.Label(self.window,justify=tk.CENTER, text="0 : silent mode, 1 (q,a) : guitar overtones, 2 (w,s) : accordion imitation, 3(e,d) : distortion").pack(side=tk.TOP)
        self.lbl_mode = tk.Label(self.window,font='Times 18', text="mode : []")  
        self.lbl_mode.pack(side=tk.TOP)
        self.lbl_FV = tk.Label(self.window, justify = tk.CENTER,font='Times 18', text="")  
        self.lbl_FV.pack(side=tk.TOP)

        self.canvas = tk.Canvas(self.window)
        self.canvas.pack(fill=tk.BOTH, expand=1)
        self.canvas.bind("<Configure>",self._on_redraw_notes)
        
        self.window.mainloop()
        
    def _on_redraw_notes(self,evnt):
        self.canvas.delete("all")
        for i in range(NOTES_COUNT-1):
            f = F_LOW*2**(i/12)
            w = evnt.width*(f-F_LOW)/(F_HIGH-F_LOW)
            self.canvas.create_line(w, 0, w, evnt.height*0.95)
 

    def _on_close_window(self):
        self.Theremin.save_wav()
        self.Theremin.Terminate()
        self.window.destroy()
    
    def _on_mouse_move(self,mouseEvent):
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        self.Theremin.set_XY(mouseEvent.x/w,1.-mouseEvent.y/h)
        self.lbl_FV.config(text=self.Theremin.get_string())

    def _on_mouse_wheel(self,mouseWheelEvent):
        TIME_STEP = 0.05
        dt = 0
        if mouseWheelEvent.delta>0:
            dt = TIME_STEP
        elif mouseWheelEvent.delta<0:
            dt = -TIME_STEP
            
        self.Theremin.frameTime = min(1,max(TIME_STEP,self.Theremin.frameTime+dt))
        self.lbl_FV.config(text=self.Theremin.get_string())

        
    def _on_key_press(self,keyEvent): 
        def _key_to_param(keycode, flip_code ,up_code,down_code, stateFlag ,paramValue):
            PARAM_STEP = 0.01
            if keycode == flip_code:
                stateFlag = not stateFlag
            elif keycode == up_code:
                paramValue += PARAM_STEP
            elif keycode == down_code:
                paramValue -= PARAM_STEP

            paramValue = min(1,max(0,paramValue))
            return stateFlag,paramValue
        # 
        key = keyEvent.keycode
        
        self.Theremin.silent, _ = _key_to_param(key, 48, None, None, self.Theremin.silent, 0)
        self.Theremin.guitar,self.Theremin.guitar_param = _key_to_param(key,49,81,65,self.Theremin.guitar,self.Theremin.guitar_param)
        self.Theremin.accordion,self.Theremin.accordion_param = _key_to_param(key,50,87,83,self.Theremin.accordion,self.Theremin.accordion_param)
        self.Theremin.distortion,self.Theremin.distortion_param = _key_to_param(key,51,69,68,self.Theremin.distortion,self.Theremin.distortion_param)        
        
        # use boolean value like index of array or dictionary : False=0 True=1 
        s1 = ('',' silent')[self.Theremin.silent]
        s2 = ('',' guitar:'+str(int(100*self.Theremin.guitar_param)))[self.Theremin.guitar]
        s3 = ('',' accordion:'+str(int(100*self.Theremin.accordion_param)))[self.Theremin.accordion]
        s4 = ('',' distortion:'+str(int(100*self.Theremin.distortion_param)))[self.Theremin.distortion]
        
        self.lbl_mode.config(text='mode : ['+s1+s2+s3+s4+' ]')

def main():
    CApplication(CThereminAudio())
    
if __name__=='__main__':
    main()