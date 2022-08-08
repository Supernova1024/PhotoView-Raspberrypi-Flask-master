import cv2
import numpy as np
import tensorflow as tf
import os
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
import time
import json
import RPi.GPIO as GPIO
import glob

#Set Up GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

#Save Photos of Trapped Animals
files = glob.glob("trapped/photo*.jpg")
if files == []:
    print "No Previous Image Found: Resetting Image Counter"
    hognum = 1000000
else:
    files = sorted(files)
    hognum = int(os.path.basename(files[-1])[5:-4])
    hognum += 1
    print "Previous Image Found and Counted - Current Image Number is:"
    print hognum

#Save Photos of Detected Motion
files2 = glob.glob("detected/photo*.jpg")
if files2 == []:
    print "No Previous Image Found: Resetting Image Counter"
    num = 1000000
else:
    files2 = sorted(files2)
    num = int(os.path.basename(files2[-1])[5:-4])
    num += 1
    print "Previous Image Found and Counted - Current Image Number is:"
    print num

#Load Parameters
params = {}
with open('/home/pi/params.json') as data_file:
    params = json.load(data_file)

#print ('=== params ===', params)

if (params['starttime']) == 'Small':
        numcts = 5
if (params['starttime']) == 'Medium':
        numcts = 10
if (params['starttime']) == 'Large':
        numcts = 15
        
# switch camera to video streaming
#cap = cv2.VideoCapture("bbvid1.mpg")
cap = cv2.VideoCapture(0)
a = []
model_dir = ''
#bgsMOG = cv2.createBackgroundSubtractorMOG2(detectShadows = False)
bgsMOG = cv2.createBackgroundSubtractorMOG2(history = 300, varThreshold = 50, detectShadows = False)

label_lines = [line.rstrip() for line 
        in tf.gfile.GFile("labels.txt")]

def create_graph():

 	# Creates graph from saved graph_def.pb.
 	with tf.gfile.FastGFile(os.path.join(
 		model_dir, 'graph.pb'), 'rb') as f:
 		graph_def = tf.GraphDef()
 		graph_def.ParseFromString(f.read())
 		_ = tf.import_graph_def(graph_def, name='')

# Download and create graph
create_graph()

def detect(frame):
 	with tf.Session() as sess:
 		softmax_tensor = sess.graph.get_tensor_by_name('final_result:0')
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
 		print ('The animal is {} and score is {}'.format(human_string_n, score))
                result = 0
                if human_string_n in ('Hog') and score > .55:
                    result = Hog
 		return result
hog = 0

# Take Sample Image to Send to Wifi Interface to check camera placement
sample = 0
framecount = 0
while sample == 0:
    ret, frame = cap.read()
    framecount += 1
    if framecount > 400 and sample < 1:
        cv2.imwrite("deer/sample.jpg", frame)
        print "Sample Image Collected"
        sample += 1

# Motion Detection Portion
while hog < 1:
        print "delay start timer 2 min"
        GPIO.setup(37, GPIO.OUT)
        GPIO.cleanup(37)
        time.sleep(10)
        GPIO.setup(37, GPIO.OUT)
        print "starting control system"
        hog = 0
        fct = 0
        timeout = time.time() + 60
        #cap = cv2.VideoCapture(0)
        time.sleep(2)
        while (hog < 1) and (time.time() < timeout):
                ret, frame = cap.read()
                fct += 1
                if ret and fct > 300:
                    fgmask = bgsMOG.apply(frame)
                    # To find the contours of the objects
                    _, contours, hierarchy = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    #cv2.drawContours(frame,contours,-1,(0,255,0),cv2.cv.CV_FILLED,32)
                    try: hierarchy = hierarchy[0]
                    except: hierarchy = []
                    a = []
                    for contour, hier in zip(contours, hierarchy):
                        if (hog < 2) and (time.time() < timeout):
                            (x, y, w, h) = cv2.boundingRect(contour)
                            if w > 30 and h > 30:
                                width = str(w)
                                height = str(h)
                                dimension = width + ", " + height
                                dimension1 = dimension
                                cv2.rectangle(frame, (x, y), (x + w, y + h), (147, 20, 255), 1)
                                cv2.putText(frame, dimension1, (x, y + h + 12), 0, 0.5, (147, 20, 255))
                                (x, y, w, h) = cv2.boundingRect(contour)

                                x1 = w / 2
                                y1 = h / 2
                                cx = x + x1
                                cy = y + y1
                                a.append([cx, cy])
                                area = cv2.contourArea(contour)
                                if (len(a) >= numcts) and (hog < 1): 
                                        
                                    cv2.imwrite("detected/photo%s.jpg" % num, frame)
                                    num += 1
                                    if detect(frame) == 'Hog':
                                        print ('Alarm! A group of Hogs was detected. please trigger the trap!')
                                        cv2.imwrite("trapped/photo%s.jpg" % hognum, frame)
                                        hognum +=1
                                        #hog += 1
                                        break
                                    else:
                                        break
                        #cv2.imshow('BGS', fgmask)
                        cv2.imshow('Ori+Bounding Box', frame)
                        key = cv2.waitKey(100)
                        if key == ord('q'):
                                break
        #cap.release()
cv2.destroyAllWindows()
if hog >= 2:
        GPIO.setup(13, GPIO.OUT)
        print "Releasing Trap"
        time.sleep(3)
        GPIO.cleanup(13)
print "Done"
