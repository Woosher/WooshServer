import time
import subprocess
import select
import thread
import os
from subprocess import call
import shlex
import glob
import tarfile
from os.path import basename
import re
import getpass
import pwd
import grp

ACCEPTED = "Accepted password"
NEW_SESSION = "New session"
REMOVED_SESSION = "Removed session"
DISCONNECTED = "Disconnected from"
NOT_FOUND = -1
sessions = []
path = r'/etc/wooshtest/packages/wooshserver/' 
logpath = "/var/log/auth.log"
logFile = path + "executelog.txt"


def main():
	resetAndListen()

def resetAndListen():
	#MAKE WOOSH DIR
	makeDir(path)
	giveUserPermission()

	#CLEAR SSH LOG
	open(logpath, 'w').close()
	createLogFile()

	#TAIL SSH LOG
	f = subprocess.Popen(['tail','-F',logpath],\
        stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	p = select.poll()
	p.register(f.stdout)

	while True:
		if p.poll(1):
			checkTail(f.stdout.readline())
		time.sleep(0.5)


'''-------------------METHODS FOR OPERATING ON FILES/FOLDERS-------------------'''

def giveUserPermission():
	username = getpass.getuser()
	uid = pwd.getpwnam(username).pw_uid
	gid = grp.getgrnam("nogroup").gr_gid
	os.chown(path, uid, gid)


def createLogFile():
	if os.path.exists(logFile):
		fh = open(logFile, "r")
	else:
		fh = open(logFile, "w")

def appendToLog(filename):
	with open(logFile,"a") as log:
		log.write(filename + " " + str(os.path.getctime(filename)) + "\r\n")

def isNewFile(filename):
	isNew = True
	if os.stat(logFile).st_size != 0:
		with open(logFile) as file:
			last_line = file.readlines()[-1]
			linesplit = last_line.split(" ")
			path = linesplit[0]
			time = linesplit[1].split("\r")[0]
			numberTime = float(time)
			newTime = float(os.path.getctime(filename))
			isNew = (int(newTime) > numberTime)
	return isNew


def make_executable(path):
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(path, mode)

def makeDir(inputPath):
	if not os.path.exists(inputPath):
		os.makedirs(inputPath)

def findNewestArchive(path):
	latest_file = None
	list_of_files = glob.glob(path +'/*.tar.gz') 
	if list_of_files:
		latest_file = max(list_of_files, key=os.path.getctime)
	return latest_file

def executeShellScriptFiles(folderpath):
	filesForExecution = []
	for file in os.listdir(folderpath):
		if file.endswith(".sh"):
			filesForExecution.append(os.path.join(folderpath,file))

	for file in filesForExecution:
		make_executable(file)
		subprocess.call([file])

def extractArchive(archive):
	destination = basename(archive).split(".")[0]
	newPath = path + destination
	makeDir(newPath)
	tar = tarfile.open(archive)
	tar.extractall(path=newPath)
	tar.close()
	return newPath


'''-------------------METHODS FOR CHECKING TAIL-------------------'''

def checkTail(line):
	words = None
	beginWork = False
	sessionId = 0
	if contains(line, ACCEPTED):
		words = ACCEPTED
	elif contains(line, NEW_SESSION):
		words = NEW_SESSION
	elif contains(line, REMOVED_SESSION):
		words = REMOVED_SESSION
		beginWork = True

	if words is not None:
		index = indexOfWords(words, line)
		sessionId = stripForId(index)
		if words == NEW_SESSION:
			sessions.append(sessionId)

	if beginWork is True:
		startThread(sessionId)

def contains(line, word_to_find):
	return word_to_find in line

def stripForId(inputsentence):
	sentence = re.sub("[^0-9]", "", inputsentence)
	#newSentence = sentence.replace(".", "")
	#stuff =  [int(s) for s in newSentence.split() if s.isdigit()]
	return int(sentence)

def indexOfWords(words, sentence):
	wordlist = words.split(" ")
	maxWords = len(wordlist)
	count = 0
	for word in wordlist:
		place = sentence.find(word)
		if place != NOT_FOUND:
			count+=1
		if count == maxWords:
			return sentence[place+len(word):]

'''-------------------METHODS FOR THREADS-------------------'''


def workerMethod(threadname, sessionId):
	newestArchive = findNewestArchive(path)
	if newestArchive is not None:
		if isNewFile(newestArchive):
			pathToExtract  = extractArchive(newestArchive)
			appendToLog(newestArchive)
			executeShellScriptFiles(pathToExtract)
	
	sessions.remove(sessionId)

def startThread(sessionId):
	if sessionId in sessions:
		thread.start_new_thread(workerMethod, ("Thread executed by session  " + str(sessionId), sessionId ))

main()

