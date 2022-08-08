import os
import json
import re
from collections import defaultdict
from os import fsync

def read():
	try:
		with open('/home/pi/params.json', 'r') as file:
		# with open('../params.json', 'r') as file:
			accounts = json.load(file)
			return accounts
	except (OSError, ValueError):  # file does not exist or is empty/invalid
		accounts = {}

def read_conf():
	myvars = {}
	# with open("../hostapd.conf") as myfile:
	with open("/etc/hostapd/hostapd.conf") as myfile:
		for line in myfile:
			name, var = line.partition("=")[::2]
			if name.strip() == 'ssid':
				return var;

def fixup(key, value):
	data = read()
	data[key] = value
	
	# write the changed value into file
	with open("/home/pi/params.json","w") as f:
	# with open("../params.json","w") as f:
		json.dump(data, f, ensure_ascii=False)
		f.close()


def updating(filename,dico):



	RE = '(('+'|'.join(dico.keys())+')\s*=)[^\r\n]*?(\r?\n|\r)'

	pat = re.compile(RE)

	def jojo(mat,dic = dico ):

		return dic[mat.group(2)].join(mat.group(1,3))

	with open(filename,'rb') as f:

		content = f.read() 

	with open(filename,'wb') as f:

		f.write(pat.sub(jojo,content))
	return

def nested_dict(n, type):
	if n == 1:
		return defaultdict(type)
	else:
		return defaultdict(lambda: nested_dict(n-1, type))