import argparse
import re
import sys
import cv2
import json
import numpy as np
import tensorflow as tf
import time
import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
from threading import Thread
import RPi.GPIO as GPIO
import glob
from PIL import Image
from shutil import copyfile
import datetime as dt

#Load Parameters
params = {}
with open('/home/pi/params.json') as data_file:
    params = json.load(data_file)

print ('=== params ===', params)

# Define num variable

files = glob.glob("deer/photo*.jpg")
if files == []:
    print "No Previous Image Found: Resetting Image Counter"
    num = 1000000
else:
    files = sorted(files)
    num = int(os.path.basename(files[-1])[5:-4])
    num += 1
    print "Previous Image Found and Counted - Current Image Number is:"
    print num

model_dir=''
 
label_lines = [line.rstrip() for line 
    in tf.gfile.GFile("labels.txt")]
 
#Set up Pins for Motion Sensors
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(29, GPIO.IN)
GPIO.setup(31, GPIO.IN)
GPIO.setup(33, GPIO.IN)
GPIO.setup(35, GPIO.IN)

#Clean up earlier pins
GPIO.setup(13, GPIO.OUT)
GPIO.cleanup(13)
GPIO.setup(15, GPIO.OUT)
GPIO.cleanup(15)
GPIO.setup(16, GPIO.OUT)
GPIO.cleanup(16)
GPIO.setup(18, GPIO.OUT)
GPIO.cleanup(18)
GPIO.setup(22, GPIO.OUT)
GPIO.cleanup(22)
GPIO.setup(32, GPIO.OUT)
GPIO.cleanup(32)
GPIO.setup(36, GPIO.OUT)
GPIO.cleanup(36)
GPIO.setup(37, GPIO.OUT)
GPIO.cleanup(37)
GPIO.setup(38, GPIO.OUT)
GPIO.cleanup(38)
GPIO.setup(40, GPIO.OUT)
GPIO.cleanup(40)
 
#Set Mode
if params['mode'] == 'Demo Mode':
    mode = "demo"
    print "Demo Mode"
elif params['mode'] == 'Demo Mode with Shocker':
    mode = "demoshock"
    print "Demo Mode Shocker"
elif params['mode'] == 'Standard Mode':
    mode = "standard"
    print "Standard Mode"
else:
    mode = "standardshock"
    print "Standard Mode Shocker"

#Set Feed Time Start Variable
if params['starttime'] == '24HR':
    feedstart = 00
elif params['starttime'] == '4AM':
    feedstart = 4
elif params['starttime'] == '5AM':
    feedstart = 5
elif params['starttime'] == '6AM':
    feedstart = 6
elif params['starttime'] == '7AM':
    feedstart = 7
elif params['starttime'] == '8AM':
    feedstart = 8
elif params['starttime'] == '9AM':
    feedstart = 9
else:
    feedstart = 10
    
#Set Feed Time Start Variable
if params['endtime'] == '24HR':
    feedstop = 23
elif params['endtime'] == '4PM':
    feedstop = 16
elif params['endtime'] == '5PM':
    feedstop = 17
elif params['endtime'] == '6PM':
    feedstop = 18
elif params['endtime'] == '7PM':
    feedstop = 19
elif params['endtime'] == '8PM':
    feedstop = 20
elif params['endtime'] == '9PM':
    feedstop = 21
else:
    feedstop = 22

#Set Feed Animal
if params['feed'] == 'Whitetail Deer':
    feed = "deer"
elif params['feed'] == 'Black Bear':
    feed = "bear"
elif params['feed'] == 'Hogs' or params['feed'] == 'Hog':
    feed = "hog"
elif params['feed'] == 'Raccoon':
    feed = "raccoon"
else:
    feed = 'aoudad'

print feedstart
print feedstop
print feed
      
# Threaded class for performance improvement
class VideoStream:
    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)
        (self.grabbed, self.frame) = self.stream.read()
        self.stopped = False
         
    def start(self):
        Thread(target=self.update, args=()).start()
        return self
  
    def update(self):
        while True:
            if self.stopped:
                self.stream.release()
                return
  
            (self.grabbed, self.frame) = self.stream.read()
  
    def read(self):
                # Return the latest frame
        return self.frame
  
    def stop(self):
        self.stopped = True

def create_graph():
 
  # Creates graph from saved graph_def.pb.
  with tf.gfile.FastGFile(os.path.join(
      model_dir, 'graph.pb'), 'rb') as f:
    graph_def = tf.GraphDef()
    graph_def.ParseFromString(f.read())
    _ = tf.import_graph_def(graph_def, name='')

# Download and create graph
create_graph()
 
# Variables declarations
frame_count=0
score=0
start = time.time()
pred=0
last=0
human_string=None
doors=0
nontarget=0
#Doors Closing
print "Doors Closing"
GPIO.setup(16, GPIO.OUT)
GPIO.setup(18, GPIO.OUT)
time.sleep(15)
GPIO.cleanup(16)
GPIO.cleanup(18)
print "Doors Closed"
 
timeout = time.time() + int(params['timer'])*60
target = 0
# Start tensorflow session
while True:
 
    #Set up motion sensor variables
    ms1=0
    ms2=0
    ms3=0
    ms4=0
 
    #clean up cameras
    GPIO.setup(36, GPIO.OUT)
    GPIO.cleanup(36)
    GPIO.setup(37, GPIO.OUT)
    GPIO.cleanup(37)
    GPIO.setup(38, GPIO.OUT)
    GPIO.cleanup(38)
    GPIO.setup(40, GPIO.OUT)
    GPIO.cleanup(40)
    if nontarget == 1 and mode in ('demo') and doors ==1:
        print "Doors Closing"
        GPIO.setup(16, GPIO.OUT)
        GPIO.setup(18, GPIO.OUT)
        time.sleep(10)
        GPIO.cleanup(16)
        GPIO.cleanup(18)
        doors = 0
        target = 0
    if nontarget == 1 and mode == 'demoshock':
        print "Shocker Activated"
        GPIO.setup(22, GPIO.OUT)
        print "Doors Closing"
        GPIO.setup(16, GPIO.OUT)
        GPIO.setup(18, GPIO.OUT)
        time.sleep(10)
        GPIO.cleanup(16)
        GPIO.cleanup(18)
        time.sleep(60)
        GPIO.cleanup(22)
        doors = 0
        target = 0
    if target == 0 and nontarget == 1 and mode == 'standardshock':
        print "Shocker Activated"
        #Turn On Shocker
        GPIO.setup(32, GPIO.OUT)
        GPIO.setup(22, GPIO.OUT)
        print "Doors Closing"
        GPIO.setup(16, GPIO.OUT)
        GPIO.setup(18, GPIO.OUT)
        time.sleep(10)
        GPIO.cleanup(16)
        GPIO.cleanup(18)
        time.sleep(180)
        GPIO.cleanup(22)
        GPIO.cleanup(32)
        doors = 0
        target = 0
    if time.time() > timeout and doors == 1:
        print "Timer Expired: Securing Machine - Resetting Timer"
        print "Closing Doors"
        GPIO.setup(16, GPIO.OUT)
        GPIO.setup(18, GPIO.OUT)
        time.sleep(10)
        GPIO.cleanup(16)
        GPIO.cleanup(18)
        print "Doors Closed"
        GPIO.cleanup(36)
        GPIO.cleanup(37)
        GPIO.cleanup(38)
        GPIO.cleanup(40)
        print "Resetting Timer"
        doors = 0
        target = 0

    print("Monitoring Motion Sensors")
    hour = dt.datetime.now().hour
    while feedstart > hour or hour > feedstop:
        print "Checking Time"
        time.sleep(300)
    while ms1 < 5 and ms2 < 5 and ms3 < 5 and ms4 < 5:
            if GPIO.input(29):
                    print("Motion Detected MS1")
                    ms1 += 1
                    time.sleep(.2)
            if ms1 == 5:
                    GPIO.setup(37, GPIO.OUT)
                    print "Camera 1 Started"
                    time.sleep(2)
                    break
            if GPIO.input(31) and mode in ('standard', 'standardshock'):
                    print("Motion Detected MS2")
                    ms2 += 1
                    time.sleep(.2)
            if ms2 == 5:
                    GPIO.setup(36, GPIO.OUT)
                    print "Camera 2 Started"
                    time.sleep(2)
                    break
            if GPIO.input(33) and mode in ('standard', 'standardshock'):
                    print("Motion Detected MS3")
                    ms3 += 1
                    time.sleep(.2)
            if ms3 == 5:
                    GPIO.setup(38, GPIO.OUT)
                    print "Camera 3 Started"
                    time.sleep(2)
                    break
            if GPIO.input(35) and mode in ('standard', 'standardshock'):
                    print("Motion Detected MS4")
                    ms4 += 1
                    time.sleep(.2)
            if ms4 == 5:
                    GPIO.setup(40, GPIO.OUT)
                    print "Camera 4 Started"
                    time.sleep(2)
                    break
            if time.time() > timeout and doors == 1:
                    print "Timer Expired: Securing Machine - Resetting Timer"
                    print "Closing Doors"
                    GPIO.setup(16, GPIO.OUT)
                    GPIO.setup(18, GPIO.OUT)
                    time.sleep(10)
                    GPIO.cleanup(16)
                    GPIO.cleanup(18)
                    print "Doors Closed"
                    GPIO.cleanup(36)
                    GPIO.cleanup(37)
                    GPIO.cleanup(38)
                    GPIO.cleanup(40)
                    print "Resetting Timer"
                    doors = 0
                    target = 0
 
    vs = VideoStream(src=0)
    vs.start()
    print "Camera Started"
    with tf.Session() as sess:
            softmax_tensor = sess.graph.get_tensor_by_name('final_result:0')
            if mode in ('standard', 'standardshock'):
                scanmax = 5
            if mode in ('demo', 'demoshock'):
                scanmax = 25
            scans = 0
            while scans < scanmax:
                    frame = vs.read()
                    frame_count+=1
                    # Only run every 5 frames
                    if frame_count%10==0:
 
                            # Save the image as the fist layer of inception is a DecodeJpeg
                            cv2.imwrite("current_frame.jpg",frame)
 
                            image_data = tf.gfile.FastGFile("./current_frame.jpg", 'rb').read()
                            predictions = sess.run(softmax_tensor,{'DecodeJpeg/contents:0': image_data})
 
                            predictions = np.squeeze(predictions)
 
                            # change n_pred for more predictions
                            n_pred=1
                            top_k = predictions.argsort()[-n_pred:][::-1]
                            for node_id in top_k:
                                    human_string_n = label_lines[node_id]
                                    score = predictions[node_id]
 
                            print (scans)
                            scans += 1
                            print('%s (score = %.2f)' % (human_string_n, score))
 
                            if human_string_n in (params['feed']) and score > .75:
                                now = time.strftime("%c")
                                font = cv2.FONT_HERSHEY_SIMPLEX
                                img = cv2.imread("/home/pi/current_frame.jpg")
                                machinename = params['name']
                                text = machinename + " - " + now
                                text2 = str(text)
                                text3 = "hello"
                                cv2.putText(frame, text2, (20,20), font, 0.8,(0,102,255), 2, cv2.LINE_AA)
                                cv2.imwrite("/home/pi/detected.jpg", frame)
                                time.sleep(2)
                                copyfile("/home/pi/detected.jpg", "/home/pi/deer/photo%s.jpg" % num)
                                try:
                                    im = Image.open("/home/pi/deer/photo%s.jpg" % num)
                                except IOError:
                                    print "File Corrupted"
                                    os.remove("/home/pi/deer/photo%s.jpg" % num)
                                print "Target Detected"
                                print ('Confidence %.2F%%' % (score * 100))
                                num += 1
                                scans = 0
                                os.remove("/home/pi/detected.jpg")
                                timeout = time.time() + int(params['timer'])*60
                                target = 1
                                if doors == 0:
                                        print "Doors Opening"
                                        GPIO.setup(13, GPIO.OUT)
                                        GPIO.setup(15, GPIO.OUT)
                                        time.sleep(10)
                                        GPIO.cleanup(13)
                                        GPIO.cleanup(15)
                                        print "Doors Open"
                                        doors = 1
                            if human_string_n in (params['never_feed']) and score >.75:
                                print "Non Target Detected"
                                nontarget=1
                                scans = scanmax
                            os.remove("/home/pi/current_frame.jpg")
                    # if the 'q' key is pressed, stop the loop
                    if cv2.waitKey(1) & 0xFF == ord("q"):break
 
            vs.stop()
            print "Closing Camera"
            time.sleep(2)
