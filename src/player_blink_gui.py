import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
import cv2
import heapq
import json
import os.path
import signal
import sys
import threading
import time
import tkinter as tk
import tkinter.filedialog as fd
import winsound
from tkinter import ttk
from os import listdir
from os.path import isfile, join
from PIL import Image, ImageTk

os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

import rngtool
from xorshift import Xorshift

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.rng = None
        self.previewing = False
        self.monitoring = False
        self.reidentifying = False
        self.tidsiding = False
        self.timelining = False
        self.config_json = {}
        self.default_config = {
            "MonitorWindow": True,
            "WindowPrefix": "SysDVR-Client [PID ",
            "image": "./images/cave/eye.png",
            "view": [0, 0, 0, 0],
            "thresh": 0.9,
            "white_delay": 0.0,
            "advance_delay": 0,
            "advance_delay_2": 0,
            "npc": 0,
            "timeline_npc": 0,
            "pokemon_npc": 0,
            "crop": [0,0,0,0],
            "camera": 0,
            "display_percent": 80
        }
        self.pack()
        self.create_widgets()
        signal.signal(signal.SIGINT, self.signal_handler)

    def update_configs(self,event=None):
        self.config_jsons =  [f for f in listdir("configs") if isfile(join("configs", f))]
        self.config_combobox['values'] = self.config_jsons

    def create_widgets(self):
        self.master.title("Player Blink")

        ttk.Label(self,text="Progress:").grid(column=0,row=0)
        ttk.Label(self,text="S[0-3]:").grid(column=0,row=3)
        ttk.Label(self,text="S[0-1]:").grid(column=0,row=7)
        ttk.Label(self,text="Advances:").grid(column=0,row=10)
        ttk.Label(self,text="Timer:").grid(column=0,row=11)
        ttk.Label(self,text="X to advance:").grid(column=0,row=12)

        self.progress = ttk.Label(self,text="0/0")
        self.progress.grid(column=1,row=0)

        self.config_combobox = ttk.Combobox(self, state="readonly", values=[])
        self.config_combobox.grid(column=2,row=0)
        self.config_combobox.bind("<<ComboboxSelected>>", self.config_combobox_onchange)
        self.config_combobox.bind("<Button-1>", self.update_configs)
        self.update_configs()

        self.new_config_button = ttk.Button(self,text="+",command=self.new_config,width=2)
        self.new_config_button.grid(column=3,row=0,columnspan=2)

        self.eye_display = ttk.Label(self)
        self.eye_display.grid(column=2,row=1)

        self.prefix_input = ttk.Entry(self)
        self.prefix_input.grid(column=2,row=2)

        ttk.Label(self,text="Camera:").grid(column=3,row=1)
        self.camera_index = tk.Spinbox(self, from_= 0, to = 99, width = 5)
        self.camera_index.grid(column=4,row=1)

        self.monitor_window_var = tk.IntVar()
        self.monitor_window = ttk.Checkbutton(self,text="Monitor Window",variable=self.monitor_window_var)
        self.monitor_window.grid(column=3,row=2,columnspan=2)

        self.monitor_display_buffer = ttk.Label(self)
        self.monitor_display_buffer.grid(column=2,row=3,rowspan=64,columnspan=2)
        self.monitor_display = ttk.Label(self)
        self.monitor_display.grid(column=2,row=3,rowspan=64,columnspan=2)

        self.monitor_blink_button = ttk.Button(self, text="Monitor Blinks", command=self.monitor_blinks)
        self.monitor_blink_button.grid(column=5,row=0)

        self.reidentify_button = ttk.Button(self, text="Reidentify", command=self.reidentify)
        self.reidentify_button.grid(column=5,row=1)

        self.preview_button = ttk.Button(self, text="Preview", command=self.preview)
        self.preview_button.grid(column=5,row=2)

        self.stop_tracking_button = ttk.Button(self, text="Stop Tracking", command=self.stop_tracking)
        self.stop_tracking_button.grid(column=5,row=3)

        self.timeline_button = ttk.Button(self, text="Timeline", command=self.timeline)
        self.timeline_button.grid(column=5,row=4)

        self.tidsid_button = ttk.Button(self, text="TID/SID", command=self.tidsid)
        self.tidsid_button.grid(column=5,row=5)

        x = y = w = h = 0
        th = 0.9

        ttk.Label(self,text="X").grid(column=6,row=1)
        ttk.Label(self,text="Y").grid(column=6,row=2)
        ttk.Label(self,text="W").grid(column=6,row=3)
        ttk.Label(self,text="H").grid(column=6,row=4)
        ttk.Label(self,text="Threshold").grid(column=6,row=5)
        ttk.Label(self,text="Time Delay").grid(column=6,row=6)
        ttk.Label(self,text="Advance Delay").grid(column=6,row=7)
        ttk.Label(self,text="Advance Delay 2").grid(column=6,row=8)
        ttk.Label(self,text="NPCs").grid(column=6,row=9)
        ttk.Label(self,text="NPCs during Timeline").grid(column=6,row=10)
        ttk.Label(self,text="Pokemon NPCs").grid(column=6,row=11)

        self.menu_check_var = tk.IntVar()
        self.menu_check = ttk.Checkbutton(self, text="+1 on menu close", variable=self.menu_check_var)
        self.menu_check.grid(column=7,row=0)
        self.menu_check_var.set(1)

        self.reident_noisy_check_var = tk.IntVar()
        self.reident_noisy_check = ttk.Checkbutton(self, text="Reident 1 PK NPC", variable=self.reident_noisy_check_var)
        self.reident_noisy_check.grid(column=5,row=6)
        self.reident_noisy_check_var.set(0)

        self.pos_x = tk.Spinbox(self, from_= 0, to = 99999, width = 5)
        self.pos_x.grid(column=7,row=1)
        self.pos_y = tk.Spinbox(self, from_= 0, to = 99999, width = 5)
        self.pos_y.grid(column=7,row=2)
        self.pos_w = tk.Spinbox(self, from_= 0, to = 99999, width = 5)
        self.pos_w.grid(column=7,row=3)
        self.pos_h = tk.Spinbox(self, from_= 0, to = 99999, width = 5)
        self.pos_h.grid(column=7,row=4)
        self.pos_th = tk.Spinbox(self, from_= 0, to = 1, width = 5, increment=0.1)
        self.pos_th.grid(column=7,row=5)
        self.whi_del = tk.Spinbox(self, from_= 0, to = 999, width = 5, increment=0.1)
        self.whi_del.grid(column=7,row=6)
        self.adv_del = tk.Spinbox(self, from_= 0, to = 999, width = 5, increment=1)
        self.adv_del.grid(column=7,row=7)
        self.adv_del_2 = tk.Spinbox(self, from_= 0, to = 999, width = 5, increment=1)
        self.adv_del_2.grid(column=7,row=8)
        self.npc = tk.Spinbox(self, from_= 0, to = 999, width = 5, increment=1)
        self.npc.grid(column=7,row=9)
        self.timeline_npc = tk.Spinbox(self, from_= -1, to = 999, width = 5, increment=1)
        self.timeline_npc.grid(column=7,row=10)
        self.pokemon_npc = tk.Spinbox(self, from_= 0, to = 999, width = 5, increment=1)
        self.pokemon_npc.grid(column=7,row=11)

        self.new_eye_button = ttk.Button(self, text="Select Eye",command=self.new_eye)
        self.new_eye_button.grid(column=6,row=12,columnspan=2)

        self.save_button = ttk.Button(self, text="Save Config",command=self.save_config)
        self.save_button.grid(column=6,row=13,columnspan=2)

        self.raw_screenshot_button = ttk.Button(self, text="Raw Screenshot",command=self.save_screenshot)
        self.raw_screenshot_button.grid(column=6,row=14,columnspan=2)

        self.s0_1_2_3 = tk.Text(self, width=10, height=4)
        self.s0_1_2_3.grid(column=1,row=2,rowspan=4)

        self.s01_23 = tk.Text(self, width=20, height=2)
        self.s01_23.grid(column=1,row=6,rowspan=4)

        self.advances = 0
        self.adv = ttk.Label(self,text=self.advances)
        self.adv.grid(column=1,row=10)

        self.count_down = 0
        self.cd = ttk.Label(self,text=self.count_down)
        self.cd.grid(column=1,row=11)

        self.advances_increase = tk.Spinbox(self, from_ = 0, to = 999999)
        self.advances_increase.grid(column=1,row=12)

        self.advances_increase_button = ttk.Button(self, text="Advance", command=self.increase_advances)
        self.advances_increase_button.grid(column=1,row=13)

        ttk.Label(self,text="Display Percent").grid(column=0,row=14)
        self.display_percent = tk.Spinbox(self, from_ = 0, to = 500)
        self.display_percent.grid(column=1,row=14)

        self.pos_x.delete(0, tk.END)
        self.pos_x.insert(0, x)
        self.pos_y.delete(0, tk.END)
        self.pos_y.insert(0, y)
        self.pos_w.delete(0, tk.END)
        self.pos_w.insert(0, w)
        self.pos_h.delete(0, tk.END)
        self.pos_h.insert(0, h)
        self.pos_th.delete(0, tk.END)
        self.pos_th.insert(0, th)
        self.whi_del.delete(0, tk.END)
        self.whi_del.insert(0, 0.0)
        self.adv_del.delete(0, tk.END)
        self.adv_del.insert(0, 0)
        self.adv_del_2.delete(0, tk.END)
        self.adv_del_2.insert(0, 0)
        self.npc.delete(0, tk.END)
        self.npc.insert(0, 0)
        self.timeline_npc.delete(0, tk.END)
        self.timeline_npc.insert(0, 0)
        self.pokemon_npc.delete(0, tk.END)
        self.pokemon_npc.insert(0, 0)
        self.camera_index.delete(0, tk.END)
        self.camera_index.insert(0, 0)
        self.advances_increase.delete(0, tk.END)
        self.advances_increase.insert(0, 165)
        self.display_percent.delete(0, tk.END)
        self.display_percent.insert(0, 100)

        self.after_task()

    def increase_advances(self):
        plus = int(self.advances_increase.get())
        self.rng.advance(plus)
        self.advances += plus

    def new_config(self):
        with fd.asksaveasfile(initialdir="./configs/", filetypes=[("JSON", ".json")]) as f:
            json.dump(self.default_config,f,indent=4)
            self.config_combobox.set(os.path.basename(f.name))
        self.config_combobox_onchange()

    def save_screenshot(self):
        with fd.asksaveasfile(initialdir="./", filetypes=[("PNG", ".png")]) as f:
            cv2.imwrite(f.name,self.raw_screenshot)

    def new_eye(self):
        self.config_json["image"] = "./"+os.path.relpath(fd.askopenfilename(initialdir="./images/", filetypes=[("Image", ".png")])).replace("\\","/")
        self.player_eye = cv2.imread(self.config_json["image"], cv2.IMREAD_GRAYSCALE)
        self.player_eye_tk = self.cv_image_to_tk(self.player_eye)
        self.eye_display['image'] = self.player_eye_tk

    def save_config(self):
        json.dump(self.config_json,open(join("configs",self.config_combobox.get()),"w"),indent=4)

    def cv_image_to_tk(self, image):
        split = cv2.split(image)
        if len(split) == 3:
            b,g,r = split
            image = cv2.merge((r,g,b))
        im = Image.fromarray(image)
        return ImageTk.PhotoImage(image=im)

    def config_combobox_onchange(self, event=None):
        self.config_json = json.load(open(join("configs",self.config_combobox.get())))
        missing = set(self.default_config.keys()).difference(self.config_json.keys())
        if len(missing) > 0:
            print(f"Config was missing the following keys {missing}\nDefaults have been added")
        for key in missing:
            self.config_json[key] = self.default_config[key]
        x,y,w,h = self.config_json["view"]
        self.pos_x.delete(0, tk.END)
        self.pos_x.insert(0, x)
        self.pos_y.delete(0, tk.END)
        self.pos_y.insert(0, y)
        self.pos_w.delete(0, tk.END)
        self.pos_w.insert(0, w)
        self.pos_h.delete(0, tk.END)
        self.pos_h.insert(0, h)
        self.pos_th.delete(0, tk.END)
        self.pos_th.insert(0, self.config_json["thresh"])
        self.whi_del.delete(0, tk.END)
        self.whi_del.insert(0, self.config_json["white_delay"])
        self.adv_del.delete(0, tk.END)
        self.adv_del.insert(0, self.config_json["advance_delay"])
        self.adv_del_2.delete(0, tk.END)
        self.adv_del_2.insert(0, self.config_json["advance_delay_2"])
        self.npc.delete(0, tk.END)
        self.npc.insert(0, self.config_json["npc"])
        self.pokemon_npc.delete(0, tk.END)
        self.pokemon_npc.insert(0, self.config_json["pokemon_npc"])
        self.timeline_npc.delete(0, tk.END)
        self.timeline_npc.insert(0, self.config_json["timeline_npc"])
        self.camera_index.delete(0, tk.END)
        self.camera_index.insert(0, self.config_json["camera"])
        self.player_eye = cv2.imread(self.config_json["image"], cv2.IMREAD_GRAYSCALE)
        self.player_eye_tk = self.cv_image_to_tk(self.player_eye)
        self.eye_display['image'] = self.player_eye_tk
        self.prefix_input.delete(0, tk.END)
        self.prefix_input.insert(0, self.config_json["WindowPrefix"])
        self.monitor_window_var.set(self.config_json["MonitorWindow"])
        self.display_percent.delete(0, tk.END)
        self.display_percent.insert(0, self.config_json["display_percent"])

    def stop_tracking(self):
        self.tracking = False

    def timeline(self):
        self.timelining = True

    def monitor_blinks(self):
        if not self.monitoring:
            self.monitor_blink_button['text'] = "Stop Monitoring"
            self.monitoring = True
            self.monitoring_thread=threading.Thread(target=self.monitoring_work)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
        else:
            self.monitor_blink_button['text'] = "Monitor Blinks"
            self.monitoring = False

    def reidentify(self):
        if not self.reidentifying:
            self.reidentify_button['text'] = "Stop Reidentifying"
            self.reidentifying = True
            self.reidentifying_thread=threading.Thread(target=self.reidentifying_work)
            self.reidentifying_thread.daemon = True
            self.reidentifying_thread.start()
        else:
            self.reidentify_button['text'] = "Reidentify"
            self.reidentifying = False

    def tidsid(self):
        if not self.tidsiding:
            self.tidsid_button['text'] = "Stop TID/SID"
            self.tidsiding = True
            self.tidsiding_thread=threading.Thread(target=self.tidsiding_work)
            self.tidsiding_thread.daemon = True
            self.tidsiding_thread.start()
        else:
            self.tidsid_button['text'] = "TID/SID"
            self.tidsiding = False

    def monitoring_work(self):
        self.tracking = False
        blinks, intervals, offset_time = rngtool.tracking_blink(self.player_eye, *self.config_json["view"], MonitorWindow=self.config_json["MonitorWindow"], WindowPrefix=self.config_json["WindowPrefix"], crop=self.config_json["crop"], camera=self.config_json["camera"], tk_window=self, th=self.config_json["thresh"])
        self.rng = rngtool.recov(blinks, intervals, npc=self.config_json["npc"])

        self.monitor_blink_button['text'] = "Monitor Blinks"
        self.monitoring = False
        self.preview()

        waituntil = time.perf_counter()
        diff = round(waituntil-offset_time)+(1 if self.menu_check_var.get() else 0)
        self.rng.getNextRandSequence(diff*(self.config_json["npc"]+1))

        state = self.rng.getState()
        s0 = f"{state[0]:08X}"
        s1 = f"{state[1]:08X}"
        s2 = f"{state[2]:08X}"
        s3 = f"{state[3]:08X}"

        s01 = s0+s1
        s23 = s2+s3

        print(s01,s23)
        print(s0,s1,s2,s3)
        self.s0_1_2_3.delete(1.0, tk.END)
        self.s01_23.delete(1.0, tk.END)

        self.s0_1_2_3.insert(1.0,s0+"\n"+s1+"\n"+s2+"\n"+s3)
        self.s01_23.insert(1.0,s01+"\n"+s23)

        self.advances = 0
        self.tracking = True
        self.count_down = None
        while self.tracking:
            if self.count_down is None:
                if self.timelining:
                    self.count_down = 10
            elif self.count_down != 0:
                self.count_down -= 1
                print(self.count_down+1)
            else:
                break

            self.advances += self.config_json["npc"]+1
            r = self.rng.getNextRandSequence(self.config_json["npc"]+1)[-1]
            waituntil += 1.018

            print(f"advances:{self.advances}, blinks:{hex(r&0xF)}")

            next_time = waituntil - time.perf_counter() or 0
            time.sleep(next_time)
        if self.timelining:
            self.rng.next()
            # white screen
            time.sleep(self.config_json["white_delay"])
            waituntil = time.perf_counter()
            self.rng.advance(self.config_json["advance_delay"])
            self.advances += self.config_json["advance_delay"]
            print("blink timeline started")
            queue = []
            for _ in range(self.config_json["timeline_npc"]+1):
                heapq.heappush(queue, (waituntil+1.017,0))
            for _ in range(self.config_json["pokemon_npc"]):
                blink_int = self.rng.rangefloat(3,12) + 0.285
                heapq.heappush(queue, (waituntil+blink_int,1))

            self.count_down = 10
            while queue and self.tracking:
                self.advances += 1
                w, q = heapq.heappop(queue)
                next_time = w - time.perf_counter() or 0
                if next_time>0:
                    time.sleep(next_time)

                if self.config_json["advance_delay_2"] != 0:
                    if self.count_down > 0:
                        self.count_down -= 1
                        print(self.count_down+1)
                    elif self.count_down != -1:
                        self.count_down -= 1
                        self.advances += self.config_json["advance_delay_2"]
                        self.rng.advance(self.config_json["advance_delay_2"])

                if q==0:
                    r = self.rng.next()
                    print(f"advances:{self.advances}, blink:{hex(r&0xF)}")
                    heapq.heappush(queue, (w+1.017, 0))
                else:
                    blink_int = self.rng.rangefloat(3,12) + 0.285

                    heapq.heappush(queue, (w+blink_int, 1))
                    print(f"advances:{self.advances}, interval:{blink_int}")
            self.timelining = False
            self.alert_user()

    def alert_user():
        # Beep so the user knows the task is finished
        frequency = 750  # Set Frequency To 750 Hertz
        duration = 100  # Set Duration To 100 ms == 0.1 second
        winsound.Beep(frequency, duration)
        time.sleep(0.1);
        winsound.Beep(frequency, duration)

    def tidsiding_work(self):
        self.tracking = False
        munchlax_intervals = rngtool.tracking_poke_blink(self.player_eye, *self.config_json["view"], MonitorWindow=self.config_json["MonitorWindow"], WindowPrefix=self.config_json["WindowPrefix"], crop=self.config_json["crop"], camera=self.config_json["camera"], tk_window=self, th=self.config_json["thresh"], size=64)
        self.rng = rngtool.recovByMunchlax(munchlax_intervals)
        state = self.rng.getState()

        self.tidsid_button['text'] = "TID/SID"
        self.tidsiding = False
        self.preview()

        s0 = f"{state[0]:08X}"
        s1 = f"{state[1]:08X}"
        s2 = f"{state[2]:08X}"
        s3 = f"{state[3]:08X}"

        s01 = s0+s1
        s23 = s2+s3

        print(s01,s23)
        print(s0,s1,s2,s3)
        self.s0_1_2_3.delete(1.0, tk.END)
        self.s01_23.delete(1.0, tk.END)

        self.s0_1_2_3.insert(1.0,s0+"\n"+s1+"\n"+s2+"\n"+s3)
        self.s01_23.insert(1.0,s01+"\n"+s23)

        waituntil = time.perf_counter()
        ts = time.time()

        print([hex(x) for x in state],ts)
        self.tracking = True
        while self.tracking:
            self.advances += 1
            interval = self.rng.rangefloat(3.0,12.0) + 0.285
            waituntil += interval

            print(f"advances:{self.advances}")

            next_time = waituntil - time.perf_counter() or 0
            time.sleep(next_time)


    def reidentifying_work(self):
        self.tracking = False
        state = [int(x,16) for x in self.s0_1_2_3.get(1.0,tk.END).split("\n")[:4]]

        s0 = f"{state[0]:08X}"
        s1 = f"{state[1]:08X}"
        s2 = f"{state[2]:08X}"
        s3 = f"{state[3]:08X}"

        s01 = s0+s1
        s23 = s2+s3

        print(s01,s23)
        print(s0,s1,s2,s3)
        self.s0_1_2_3.delete(1.0, tk.END)
        self.s01_23.delete(1.0, tk.END)

        self.s0_1_2_3.insert(1.0,s0+"\n"+s1+"\n"+s2+"\n"+s3)
        self.s01_23.insert(1.0,s01+"\n"+s23)

        print([hex(x) for x in state])
        if self.reident_noisy_check_var.get():
            self.pokemon_npc.delete(0,tk.END)
            self.pokemon_npc.insert(0,1)
            observed_blinks, observed_intervals, offset_time = rngtool.tracking_blink(self.player_eye, *self.config_json["view"], MonitorWindow=self.config_json["MonitorWindow"], WindowPrefix=self.config_json["WindowPrefix"], crop=self.config_json["crop"], camera=self.config_json["camera"], tk_window=self, th=self.config_json["thresh"], size=20)
            self.rng, adv = rngtool.reidentifyByIntervalsNoisy(Xorshift(*state), observed_intervals)
            self.timelining = True
            self.count_down = 0
            auto_timeline = True
        else:
            observed_blinks, observed_intervals, offset_time = rngtool.tracking_blink(self.player_eye, *self.config_json["view"], MonitorWindow=self.config_json["MonitorWindow"], WindowPrefix=self.config_json["WindowPrefix"], crop=self.config_json["crop"], camera=self.config_json["camera"], tk_window=self, th=self.config_json["thresh"], size=7)
            self.rng, adv = rngtool.reidentifyByIntervals(Xorshift(*state), observed_intervals, return_advance=True, npc=self.config_json["npc"])
            auto_timeline = False

        self.reidentify_button['text'] = "Reidentify"
        self.reidentifying = False
        self.preview()

        waituntil = time.perf_counter()
        diff = round(waituntil-offset_time)+(1 if self.menu_check_var.get() else 0)
        self.rng.getNextRandSequence(diff*(self.config_json["npc"]+1))
        state = self.rng.getState()

        self.advances = adv+diff*(self.config_json["npc"]+1)
        self.tracking = True
        if not auto_timeline:
            self.count_down = None
        while self.tracking:
            if self.count_down is None:
                if self.timelining:
                    self.count_down = 10
            elif self.count_down != 0:
                self.count_down -= 1
                print(self.count_down+1)
            else:
                break

            self.advances += self.config_json["npc"]+1
            r = self.rng.getNextRandSequence(self.config_json["npc"]+1)[-1]
            waituntil += 1.018

            print(f"advances:{self.advances}, blinks:{hex(r&0xF)}")

            next_time = waituntil - time.perf_counter() or 0
            time.sleep(next_time)
        if self.timelining:
            self.rng.next()
            # white screen
            time.sleep(self.config_json["white_delay"])
            waituntil = time.perf_counter()
            self.rng.advance(self.config_json["advance_delay"])
            self.advances += self.config_json["advance_delay"]
            print("blink timeline started")
            queue = []
            for _ in range(self.config_json["timeline_npc"]+1):
                heapq.heappush(queue, (waituntil+1.017,0))
            for _ in range(self.config_json["pokemon_npc"]):
                blink_int = self.rng.rangefloat(3,12) + 0.285
                heapq.heappush(queue, (waituntil+blink_int,1))

            self.count_down = 10
            while queue and self.tracking:
                self.advances += 1
                w, q = heapq.heappop(queue)
                next_time = w - time.perf_counter() or 0
                if next_time>0:
                    time.sleep(next_time)

                if self.config_json["advance_delay_2"] != 0:
                    if self.count_down > 0:
                        self.count_down -= 1
                        print(self.count_down+1)
                    elif self.count_down != -1:
                        self.count_down -= 1
                        self.advances += self.config_json["advance_delay_2"]
                        self.rng.advance(self.config_json["advance_delay_2"])

                if q==0:
                    r = self.rng.next()
                    print(f"advances:{self.advances}, blink:{hex(r&0xF)}")
                    heapq.heappush(queue, (w+1.017, 0))
                else:
                    blink_int = self.rng.rangefloat(3,12) + 0.285

                    heapq.heappush(queue, (w+blink_int, 1))
                    print(f"advances:{self.advances}, interval:{blink_int}")
            self.timelining = False
            self.alert_user()

    def preview(self):
        if not self.previewing:
            self.preview_button['text'] = "Stop Preview"
            self.previewing = True
            self.previewing_thread=threading.Thread(target=self.previewing_work)
            self.previewing_thread.daemon = True
            self.previewing_thread.start()
        else:
            self.preview_button['text'] = "Preview"
            self.previewing = False

    def previewing_work(self):
        last_frame_tk = None
        last_camera = self.config_json["camera"]

        if self.config_json["MonitorWindow"]:
            from windowcapture import WindowCapture
            video = WindowCapture(self.config_json["WindowPrefix"],self.config_json["crop"])
        else:
            if sys.platform.startswith('linux'): # all Linux
                backend = cv2.CAP_V4L
            elif sys.platform.startswith('win'): # MS Windows
                backend = cv2.CAP_DSHOW
            elif sys.platform.startswith('darwin'): # macOS
                backend = cv2.CAP_ANY
            else:
                backend = cv2.CAP_ANY # auto-detect via OpenCV
            video = cv2.VideoCapture(self.config_json["camera"],backend)
            video.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
            video.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
            video.set(cv2.CAP_PROP_BUFFERSIZE,1)
            print(f"camera {self.config_json['camera']}")


        while self.previewing:
            if self.config_json["camera"] != last_camera:
                video = cv2.VideoCapture(self.config_json["camera"],backend)
                video.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
                video.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
                video.set(cv2.CAP_PROP_BUFFERSIZE,1)
                print(f"camera {self.config_json['camera']}")
                last_camera = self.config_json["camera"]

            eye = self.player_eye
            w, h = eye.shape[::-1]
            roi_x, roi_y, roi_w, roi_h = self.config_json["view"]
            _, frame = video.read()
            if frame is not None:
                roi = cv2.cvtColor(frame[roi_y:roi_y+roi_h,roi_x:roi_x+roi_w],cv2.COLOR_RGB2GRAY)
                res = cv2.matchTemplate(roi,eye,cv2.TM_CCOEFF_NORMED)
                _, match, _, max_loc = cv2.minMaxLoc(res)

                cv2.rectangle(frame,(roi_x,roi_y), (roi_x+roi_w,roi_y+roi_h), (0,0,255), 2)
                if 0.01<match<self.config_json["thresh"]:
                    cv2.rectangle(frame,(roi_x,roi_y), (roi_x+roi_w,roi_y+roi_h), 255, 2)
                else:
                    max_loc = (max_loc[0] + roi_x,max_loc[1] + roi_y)
                    bottom_right = (max_loc[0] + w, max_loc[1] + h)
                    cv2.rectangle(frame,max_loc, bottom_right, 255, 2)
                self.raw_screenshot = frame
                if self.config_json["display_percent"] != 100:
                    _, fw, fh = frame.shape[::-1]
                    frame = cv2.resize(frame,(round(fw*self.config_json["display_percent"]/100),round(fh*self.config_json["display_percent"]/100)))
                frame_tk = self.cv_image_to_tk(frame)
                self.monitor_tk_buffer = last_frame_tk
                self.monitor_display_buffer['image'] = self.monitor_tk_buffer
                self.monitor_tk = frame_tk
                self.monitor_display['image'] = self.monitor_tk
                last_frame_tk = frame_tk
        self.monitor_tk_buffer = None
        self.monitor_tk = None

    def after_task(self):
        self.config_json["view"] = [int(self.pos_x.get()),int(self.pos_y.get()),int(self.pos_w.get()),int(self.pos_h.get())]
        self.config_json["thresh"] = float(self.pos_th.get())
        self.config_json["WindowPrefix"] = self.prefix_input.get()
        self.config_json["white_delay"] = float(self.whi_del.get())
        self.config_json["advance_delay"] = int(self.adv_del.get())
        self.config_json["advance_delay_2"] = int(self.adv_del_2.get())
        self.config_json["npc"] = int(self.npc.get())
        self.config_json["pokemon_npc"] = int(self.pokemon_npc.get())
        self.config_json["timeline_npc"] = int(self.timeline_npc.get())
        self.config_json["MonitorWindow"] = bool(self.monitor_window_var.get())
        self.config_json["camera"] = int(self.camera_index.get())
        self.config_json["display_percent"] = int(self.display_percent.get())
        self.adv['text'] = self.advances
        self.cd['text'] = self.count_down
        self.after(100,self.after_task)

    def signal_handler(self, signal, frame):
        sys.exit(0)

root = tk.Tk()
app = Application(master=root)
app.mainloop()
