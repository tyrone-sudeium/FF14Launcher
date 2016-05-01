#!/usr/bin/env python3
# FFXIV ARR Python Launcher - Python 2 or 3
# Author: Jordan Henderson
# This is a fairly quick and nasty implementation of a functional launcher for FFXIV.
# TODO: ffxivupdate support.
# refactoring and changes: Matthew Clark, Arthur Moore, Stian E. Syvertsen


import re
import os
import hashlib
import sys
import ssl
from getpass import getpass
if (sys.version_info >= (3,0)):
    from urllib.request import Request,urlopen
    from urllib.parse import urlencode
    from configparser import ConfigParser
else:
    from urllib2 import  Request,urlopen
    from urllib  import urlencode
    from ConfigParser import ConfigParser

def open_url(url,data,headers,context=None):
    req = Request(url, data, headers)
    return urlopen(req,context=context)

def gen_hash(file):
	return str(os.stat(file).st_size) + "/" + hashlib.sha1(open(file, "rb").read()).hexdigest()

#Performs login routine to get sid
def login(region,username,password,one_time_password):
	#Get the login page for the region
	headers = {"User-Agent":"SQEXAuthor/2.0.0(Windows 6.2; ja-jp; ecf4a84335)"}
	login_url = "https://ffxiv-login.square-enix.com/oauth/ffxivarr/login/top?lng=en&rgn="+region
	login_info = open_url(login_url, None, headers)
	cookies = login_info.headers.get('Set-Cookie')
	if (cookies == None):
		cookies = ""
	response = login_info.read().decode('utf-8')
	m = re.search('<input type="hidden" name="_STORED_" value="(.*)"', response)
	if not m:
		raise Exception("Unable to access login page. Please try again.")

	#Authenticate with the server, and get the sid
	headers = {
		"User-Agent":"SQEXAuthor/2.0.0(Windows 6.2; ja-jp; ecf4a84335)",
		"Cookie": cookies,
		"Referer": login_url,
		"Content-Type": "application/x-www-form-urlencoded"
	}
	login_data = urlencode({'_STORED_':m.group(1), 'sqexid':username, 'password':password, 'otppw':one_time_password}).encode('utf-8')
	login_url_2 = "https://ffxiv-login.square-enix.com/oauth/ffxivarr/login/login.send"
	response = open_url(login_url_2, login_data, headers).read().decode('utf-8')
	m = re.search('login=auth,ok,sid,(.+?),', response)
	if not m:
		raise Exception("Login failed. Please try again.")

	return m.group(1)

#Use the patch gamever service to retrieve our *actual* sid.
#Also return's the game's version
def get_actual_sid(sid,gamepath):
	version = ""
	with open(gamepath+'/game/ffxivgame.ver', 'r') as f:
		version = f.readline()
	headers = {"X-Hash-Check":"enabled"}
	gamever_url = "https://patch-gamever.ffxiv.com/http/win32/ffxivneo_release_game/"+version+"/"+sid
	#calculate hashes...
	hash_str = "ffxivboot.exe/"     + gen_hash(gamepath+"/boot/ffxivboot.exe") \
		+ ","+ "ffxivlauncher.exe/" + gen_hash(gamepath+"/boot/ffxivlauncher.exe") \
		+ ","+ "ffxivupdater.exe/"  + gen_hash(gamepath+"/boot/ffxivupdater.exe")

	gamever_result = open_url(gamever_url, hash_str.encode('utf-8'), headers, ssl._create_unverified_context()).info()
	if (gamever_result.get("X-Latest-Version") != version):
		raise Exception("Game out of date.  Please run the official launcher to update it.")
	actual_sid = gamever_result.get("X-Patch-Unique-Id")
	return (actual_sid,version)

def gen_launcher_string(settings):
	launcher_str = '{wine_command}' \
		+' \'{path}/game/ffxiv.exe\'' \
		+' "language=1"' \
		+' "DEV.UseSqPack=1" "DEV.DataPathType=1"' \
		+' "DEV.LobbyHost01=neolobby01.ffxiv.com" "DEV.LobbyPort01=54994"' \
		+' "DEV.LobbyHost02=neolobby02.ffxiv.com" "DEV.LobbyPort02=54994"' \
		+' "DEV.TestSID={actual_sid}"' \
		+' "DEV.MaxEntitledExpansionID={expansion_id}"' \
		+' "SYS.Region={region}"' \
		+' "ver={version}"'
	return launcher_str.format(**settings)

def run(settings):
	sid=login(settings['region'],settings['user'],settings['password'],settings['one_time_password'])
	(settings['actual_sid'],settings['version']) = get_actual_sid(sid,settings['path'])
	launch = gen_launcher_string(settings)
	print(launch)
	os.system(launch)

def run_cli(settings):
	if (settings['user'] == ''):
		settings['user'] = raw_input("User Name:  ")
	if (settings['password'] == ''):
		settings['password'] = getpass()
	try:
		run(settings)
	except Exception as err:
		print("Error:  " + str(err))

class gui_prompt:
	def run_gui(self):
		#Store the user input
		settings['user']=self.E1.get();
		settings['password']=self.E2.get();
		settings['one_time_password']=self.E3.get()
		#Disable the GUI
		self.top.quit()
		self.top.destroy()
		#Run the Program
		try:
			run(settings)
		except Exception as err:
			if (sys.version_info >= (3,0)):
				import tkinter
				from tkinter.messagebox import showwarning
			else:
				import Tkinter as tkinter
				from tkMessageBox import showwarning
			top = tkinter.Tk()
			top.wm_withdraw()
			showwarning("Error", str(err), parent=top)

	def __init__(self,settings):
		if (sys.version_info >= (3,0)):
			import tkinter
		else:
			import Tkinter as tkinter
		self.top = tkinter.Tk()

		self.L1 = tkinter.Label(self.top, text="User Name")
		self.L1.grid(row = 0, column = 0)
		self.E1 = tkinter.Entry(self.top, textvariable=tkinter.StringVar(value=settings['user']))
		self.E1.grid(row = 0, column = 1)
		self.L2 = tkinter.Label(self.top, text="Password")
		self.L2.grid(row = 1, column = 0)
		self.E2 = tkinter.Entry(self.top, show="*", textvariable=tkinter.StringVar(value=settings['password']))
		self.E2.grid(row = 1, column = 1)
		self.L3 = tkinter.Label(self.top, text="One Time Password")
		self.L3.grid(row = 2, column = 0)
		self.E3 = tkinter.Entry(self.top, textvariable=tkinter.StringVar(value=settings['one_time_password']))
		self.E3.grid(row = 2, column = 1)

		self.OK = tkinter.Button(self.top, text ="Connect", command = self.run_gui)
		self.OK.grid(row = 3, column = 1)
		self.top.bind('<Return>', lambda _: self.OK.invoke())
		self.top.bind('<KP_Enter>', lambda _: self.OK.invoke())

		#Place window in center of screen
		self.top.eval('tk::PlaceWindow %s center' % self.top.winfo_pathname(self.top.winfo_id()))
		#Focus on the one time password box at start
		self.E3.focus()
		self.top.title("FFXIV Launcher")
		self.top.mainloop()

config_path=os.path.dirname(os.path.realpath(sys.argv[0]))
config = ConfigParser()
config.read(config_path+'/launcher_config.ini')
settings = config._sections['FFXIV']

if len(sys.argv) > 1:
	settings['one_time_password'] = sys.argv[1]

if (config['FFXIV'].getboolean('USEGUI')):
	gui_prompt(settings)
else:
	run_cli(settings)
