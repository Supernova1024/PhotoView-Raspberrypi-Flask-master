from flask_mysqldb import MySQL
from flask import Flask, request, session, g, redirect, url_for, \
	 abort, render_template, flash, send_from_directory
from contextlib import closing
from app import app
import os
from shutil import copyfile
from os import listdir, mkdir
from os.path import isdir, join, dirname, exists, splitext
from PIL import Image
import subprocess
from app.process import read, fixup, updating, read_conf, nested_dict
import time

# app = Flask(__name__)
mysql = MySQL()
# MySQL Configuration
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'raspberrypi'
app.config['MYSQL_HOST'] = 'localhost'
mysql.init_app(app)

# from app.harpu import run

app.config.update(dict(
	PHOTO_DIR='/home/pi/deer/',
	#PHOTO_DIR='static/images/',
	THUMB_SIZE=(300, 300)
))
app.config.from_envvar('PHOTOVIEWER_SETTINGS', silent=True)


@app.route('/')
@app.route('/index')
@app.route('/index/', methods=['POST'])
def index():
	return render_template('index.html')


@app.route('/mode/', methods=['POST'])
def mode():
	data = read()
	modelist = ["Demo Mode", "Demo Mode with Shocker", "Standard Mode", "Standard Mode with Shocker"]
	modemessage = 'Please select the machine mode below. Demo mode only operates one camera for demonstration purposes. Standard mode is normal operation of all cameras and sensors.'
	return render_template('mode.html', modelist=modelist, mode=data['mode'], message=modemessage);

@app.route('/machinemode/', methods=['POST'])
def machinemode():
	mode = request.form["mode"]
	fixup('mode', mode)
	time.sleep(1)
	modewarning = "Machine Mode Confirmed"
	os.system('sudo pkill -9 -f harpu.py')
	subprocess.Popen(['lxterminal', '-e', 'sudo', 'python', 'harpu.py'])
	return render_template('savesettings.html', message=modewarning)

@app.route('/delete_activities/', methods=['POST'])
def delete_activities():
	cur = mysql.connection.cursor()
	cur.execute('''DELETE FROM `records` WHERE 1''')
	mysql.connection.commit()
	deletemessage = 'All Records were Deleted.'
	return render_template('confirm.html', message=deletemessage)

@app.route('/species/', methods=['POST'])
def species():
	speciesmessage = "Please Select the Species that you wish for the machine to feed and the Species that wish the machine to never feed."
	feed = ["Whitetail Deer", "Hog", "Aoudad"]
	never_feed = ["Aoudad", "Whitetail Deer", "Hog", "Raccoon", "Black Bear"]
	data = read()
	return render_template('species.html', fdata=feed, ndata=never_feed, feed=data['feed'], never_feed=data['never_feed'], message=speciesmessage)

@app.route('/activity/', methods=['POST'])
def activity():
	recentactivity = "Recent Activity"
	animals = ['Whitetail Deer', 'Hog', 'Black Bear']
	timezones = [
		'12AM - 3AM',
		'3AM - 6AM',
		'6AM - 9AM',
		'9AM - 12PM',
		'12PM - 3PM',
		'3PM - 6PM',
		'6PM - 9PM',
		'9PM - 12AM'
	]
	data_item = [[0 for k in range(3)] for j in range(8)]
	cur = mysql.connection.cursor()
	print ('connected !!')
	cur.execute('''SELECT * FROM records''')
	results = [dict(animal=row[1], date=row[3], timezone=row[4]) for row in cur.fetchall()]
	datelist = []
	for item in results:
		if item['date'] in datelist:
			pass
		else:
			datelist.append(item['date'])

	recentactivity = nested_dict(3, int)
	for date in datelist:
		for animal in animals:
			for timezone in timezones:
				recentactivity[date][animal][timezone] = 0
	for item in results:
		recentactivity[item['date']][item['animal']][item['timezone']] += 1
	print ("recentactivity", recentactivity) 
	
	return render_template('recentactivity.html',
	 dates=datelist,
	 timezones=timezones,
	 animals=animals,
	 message=recentactivity)

@app.route('/name/', methods=['POST'])
def name():
	name = read_conf()
	print ('======= data ======', name)
	namemessage = "Please enter a name for the machine, this will also be your WIFI Network Name. After Clicking Save your machine will reboot."
	return render_template('name.html', name=name, message=namemessage)

@app.route('/timer/', methods=['POST'])
def timer():
	data = read()
	timermessage = "Please enter the number of whole minutes that you wish the machine to stay open after seeing a target animal."
	return render_template('timer.html', timer=data['timer'], message=timermessage)

@app.route('/ftime/', methods=['POST'])
def ftime():
	data = read()
	sTime = ["24HR", "4AM", "5AM", "6AM", "7AM", "8AM", "9AM", "10AM"]
	eTime = ["24HR", "4PM", "5PM", "6PM", "7PM", "8PM", "9PM", "10PM"]
	ftimemessage = "Please select when you would like the feeder to start and stop feeding. If you would like it to always feed, select 24HR on both options."
	return render_template('feedtime.html', sTime=sTime, eTime=eTime, startTime=data['starttime'], endTime=data['endtime'], message=ftimemessage)

@app.route('/feedtime/', methods=['POST'])
def feedtime():
	starttime = request.form["starttime"]
	endtime = request.form["endtime"]
	start = str(starttime)
	end = str(endtime)
	fixup('starttime', starttime)
	fixup('endtime', endtime)
	time.sleep(1)
	if start == '24HR' and end == '24HR':
		feedtimewarning = "Machine will feed 24 hours per day."
	else: 
		feedtimewarning = "Machine will Feed from "+ start + ":00 to " + end + ":00"
	os.system('sudo pkill -9 -f harpu.py')
	subprocess.Popen(['lxterminal', '-e', 'sudo', 'python', 'harpu.py'])
	return render_template('savesettings.html', message=feedtimewarning)

@app.route('/restore/', methods=['POST'])
def restore():
	restorewarning = 'The Factory Restore will reset the machine completely to factory settings this includes your WIFI name. This will also reboot your machine.'
	return render_template('restore.html', message=restorewarning)

@app.route('/confirmrestore/', methods=['POST'])
def confirmrestore():
	os.system('sudo pkill -9 -f harpu.py')
	os.system('sudo rm -rf deer')
	os.system('mkdir deer')
	os.system('sudo cp /home/pi/paramsdefault.json /home/pi/params.json')
	name = 'SpeciesSpecific'
	var_key = ['ssid']
	var_value = [name]
	what_to_change = dict(zip(var_key, var_value))
	print ('what', what_to_change)
	updating('/etc/hostapd/hostapd.conf', what_to_change)
	time.sleep(2)
	os.system('sudo reboot')

@app.route('/cancelrestore/', methods=['POST'])
def cancelrestore():
	cancelmessage = 'Restoration Cancelled, Machine not Restored'
	return render_template('index.html', message=cancelmessage)

@app.route('/imgdelete/', methods=['POST'])
def imgdelete():
	deletewarning = 'This will delete all photos from the machine. Please either Confirm or Cancel below'
	return render_template('deleteall.html', message=deletewarning)

@app.route('/canceldelete/', methods=['POST'])
def canceldelete():
	candelmessage = 'Delete Cancelled, No Images Were Deleted'
	return render_template('index.html', message=candelmessage)

@app.route('/deleteall/', methods=['POST'])
def deleteall():
	os.system('sudo pkill -9 -f harpu.py')
	os.system('sudo rm -rf deer')
	os.system('mkdir deer')
	os.system('sudo pkill -9 -f harpu.py')
	subprocess.Popen(['lxterminal', '-e', 'sudo', 'python', 'harpu.py'])
	deletemessage = 'All Images were Deleted, Please allow time for machine to restart'
	return render_template('confirm.html', message=deletemessage)

# Added by Lee Yam Keng - 09/19/2017
@app.route('/define_feeds/', methods=['POST'])
def define_feeds():
	animals_feed = request.form.getlist("feed")
	animals_not_feed = request.form.getlist("never_feed")
	print ('animals_not_feed', animals_not_feed)
	fixup('feed', animals_feed)
	fixup('never_feed', animals_not_feed)
	time.sleep(1)
	os.system('sudo pkill -9 -f harpu.py')
	subprocess.Popen(['lxterminal', '-e', 'sudo', 'python', 'harpu.py'])
	return render_template('savesettings.html')

@app.route('/define_name/', methods=['POST'])
def define_name():
	name = request.form["name"]
	print ('name', name)
	fixup('name', name)
	var_key = ['ssid']
	var_value = [name]
	what_to_change = dict(zip(var_key, var_value))
	print ('what', what_to_change)
	updating('/etc/hostapd/hostapd.conf', what_to_change)
	time.sleep(2)
	os.system('sudo reboot')

@app.route('/define_timer/', methods=['POST'])
def define_timer():
	timer = request.form["timer"]
	fixup('timer', timer)
	time.sleep(1)
	os.system('sudo pkill -9 -f harpu.py')
	subprocess.Popen(['lxterminal', '-e', 'sudo', 'python', 'harpu.py'])
	return render_template('savesettings.html')
@app.route('/delete/<filename>')
def delete(filename):
	print ('filename', filename)
	os.remove('/home/pi/deer/' + filename)
	return render_template('index.html')
			
@app.route('/thumb/<path:path>')
def thumb(path):
	# print ('--- path----', path)
	return send_from_directory('/home/pi/deer/.thumbnail/', path)

# End of plugin by Lee Yam Keng

@app.route('/settime/', methods=['POST'])
def settime():
	settimewarning = 'Please Set the Time Below'
	return render_template('form.html', message=settimewarning)

@app.route('/getresults/', methods=['POST'])
def getsresults():
	year1 = request.form['year']
	month = request.form['month']
	date1 = request.form['date']
	hour1 = request.form['hour']
	minute1 = request.form['minute']
	year = str(year1).zfill(4)
	date = str(date1).zfill(2)
	hour = str(hour1).zfill(2)
	minute = str(minute1).zfill(2)
	td = date + " " + month + " " + year + " " + hour + ":" + minute + ":00"
	td2 = str(td)
	os.system('date -s "%s" '%(td2))
	os.system('sudo hwclock -w')
	os.system('sudo pkill -9 -f harpu.py')
	subprocess.Popen(['lxterminal', '-e', 'sudo', 'python', 'harpu.py'])
	resultswarning = 'Date and Time set to: ' + month + " " + date + " " + year +"   " + hour + ":" + minute + ":00"
	return render_template('savesettings.html', message=resultswarning)

@app.route('/images/', defaults={'path': ''}, methods=['POST'])
@app.route('/<path:path>')
def photo_dir(path):
	DEBUG=True,
	pd = app.config['PHOTO_DIR']
	dir_entries = []
	image_entries = []
	up = None

	# Only add 'up' if not in the root
	if path != '':
		up = dirname(join('/',path))

	# One thing that flask does not have by default is regualar expression
	# matching in the routing. Can be added on:
	# http://stackoverflow.com/questions/5870188/does-flask-support-regular-expressions-in-its-url-routing
	# Just handle it here by checking if the current path is a directory or not

	nav = join(pd, path)
	print ('==== nav ===', nav)
	# If it's a directory, show the listing
	if isdir(nav):
	
		# TODO There is no safety here, a user could potentially navigate
		# outside of where they should be allowed

		# If there is no thumbnail directory for this directory, create it
		thumb_dir = join(nav, '.thumbnail')
		if not exists(thumb_dir):
			mkdir(thumb_dir)


		list_all = listdir(nav)
		for list_item in list_all:
			if isdir(join(nav,list_item)) and list_item != '.thumbnail':
				dir_entries.append(list_item)
			# Primitive check for image files, only for jpg and png
			elif list_item.endswith('.png') or list_item.endswith('.jpg'):
				image_entries.append(list_item)

				# Generate thumbnails for any that are missing
				thumb = join(thumb_dir,list_item)
				if not exists(thumb):
					# Open primary image
					im = Image.open(join(nav,list_item))
					# Convert mode on paletted image formats
					if im.mode != "RGB":
						im = im.convert("RGB")
					im.thumbnail(app.config['THUMB_SIZE'], Image.ANTIALIAS)
					im.save(thumb, "JPEG")
		print ('dir_entries', dir_entries)
		print ('image_entries', image_entries)
		print ('path', path)
		print ('up', up)
		
		return render_template('photo_dir.html', dir_entries=dir_entries, image_entries=image_entries, path=path, up=up)

	# Otherwise it must be a file (assuming an image file, but again, unsafe)
	# So display the photo
	else:
		return render_template('photo.html', image=url_for("static", filename=join('images', path)), file=path)