import sys, time, msvcrt
import httplib
import time
import pyttsx
import random
import winsound
from datetime import datetime

timeout = 5
inp = None
command = None
exitProg = None
keys = '00'
maxResponseTime = 0
minResponseTime = 100
bandCount = 0
baseCount = 0
timeOffset = 0
sendShock = 'false'

textToSpeech = pyttsx.init() # start voice engine

if len(sys.argv) == 2:      # One argument - timeout
  timeout = int(sys.argv[1])

# Create a random number that will go in the movement field. This will identify this session
movementInt = random.randint(1, 4000)
movementStr = str(hex(movementInt )[2:].zfill(4)) #cut off first 2 characters (0x) and fill to be 4 characters long
print "Random movement data = ", str(movementInt) #this is what will appear in the banddata
  
#print "gfhgfhfgh  \n \n "

testSystem = 'Dev'
portalUrl = 'acticheckdevcomms.azurewebsites.net'
BaseMac = 'B4994C32FFA7' #user acticheck.user+gsmtest@gmail.com
BasePasscode = '681A'  # Swap bytes
BandMac = '1862e44d3713' 
BandPasscode = '1014' # Swap bytes
BandFallMode = '6A' # change to stop annoying message in DebugLog

print '\n \n Using base ' , BaseMac, ' band ' , BandMac, ' Server ', portalUrl, '\n \n '
	
print "Press a for alert, c for cancel, s for shock or any other key to exit .. "
packetCount = 0
totalTime = 0
while True:
	# create HEX count strings
	baseCount = (baseCount + 1) % 256
	baseCountStr = str(hex(baseCount)[2:].zfill(2))
	bandCount = (bandCount + 1) % 256
	bandCountStr = str(hex(bandCount)[2:].zfill(2))

	start = time.time()	
	now = datetime.now()
	# Create 6 character string of min,sec.ms - Sent as accel XYZ
	#timeString = str(a.minute)[:2].zfill(2) + str(a.second)[:2].zfill(2) + str(a.microsecond)[:2].zfill(2)
	timeString = str(hex(now.minute)[2:].zfill(2)) + str(hex(now.second)[2:].zfill(2)) + str(hex(now.microsecond)[2:3].zfill(2))
	#print timeString
	#print a
	
	printTime = datetime.now().strftime('%H:%M:%S.%f')

	#connection =  httplib.HTTPSConnection(portalUrl, timeout=15) # test for https
	connection =  httplib.HTTPConnection(portalUrl, timeout=15)
	body_content = '|BDSTAT:'+BandMac+',706266'+keys+movementStr+timeString+'898162'+BandFallMode+baseCountStr+BandPasscode+'|BSSTAT:'+BaseMac+',01710109FFFF2043C201000155'+baseCountStr+BasePasscode+'||'				
	#print body_content
	try:
	# send message 
		connection.request('PUT', '/CommsMsg', body_content)
		# wait for response - catch timeouts
		result = connection.getresponse()		
		end = time.time()
		#print(result.status, result.reason)
		# Save message content
		content = result.read()
		# close connection
		connection.close()
		# calculate elapsed time
		elapsed = end - start
		if elapsed > maxResponseTime:
			maxResponseTime = elapsed
		if elapsed < minResponseTime:
			minResponseTime = elapsed
		dotCount = elapsed * 20
		dotString = '.'
		if dotCount > 40:
			dotCount = 40
		while dotCount > 0:
			dotCount -= 1
			dotString += '.' 
		packetCount = packetCount + 1
		totalTime = totalTime + elapsed
		# Decode special debug message
		if "Memory" in content:
			try:
				todayDate = datetime.today().strftime('%Y-%m-%d')
				debugList = content.split()
				azureArrive = todayDate + ' ' + debugList[0]
				azureExit = todayDate + ' ' + debugList[2][:-1]  # remove extra dot
				azureArriveTime = datetime.strptime(azureArrive, '%Y-%m-%d %H:%M:%S.%f')
				azureExitTime   = datetime.strptime(azureExit, '%Y-%m-%d %H:%M:%S.%f')
				AzureProcess = azureExitTime - azureArriveTime #time from message arriving in azure to response being sent
				AzureProcessSecs = AzureProcess.total_seconds()
				requestToAzure = (azureArriveTime - now).total_seconds() #time from this request to being recieved in Azure - will have clock offset
				print result.status, result.reason, ", %s, arrive (+offset) %.2f, azure %.2f, total %.2f, %s" %( printTime, requestToAzure, AzureProcessSecs, elapsed, dotString)
			except Exception as e:
				print(e)
		else:			
			#print testSystem, result.status, result.reason, "Message %d Sent on %s response time %.2f min %.2f max %.2f" % (bandCount, printTime, elapsed, minResponseTime, maxResponseTime) 
			print result.status, result.reason, content, ", %s, %.2f, %s" %( printTime, elapsed, dotString)
		#print result.status, result.reason, content, ", %s, %.2f, %s" %( printTime, elapsed, dotString)
		if elapsed > 1.5:
			winsound.Beep(1500,300) # 1500Hz, 300ms
		#if content:
		#	print content
		# Process response
		baseMessage = ' ' #default to null
		bandMessage = ' ' #default to null
		baseContent = content.find('DBSCMD')
		bandContent = content.find('DBDCMD')
		if (baseContent > 0):
			baseMessage = content[baseContent + 20:baseContent + 52]
			tune = baseMessage[4:6]
			# pre-alert 81, alert 80, all clear 06
			if tune != '00':
				print 'Base tune ', tune
				if tune == '81':
					textToSpeech.say('Pre alert')
				if tune == '80':
					textToSpeech.say('Alert')
				if tune == '06':
					textToSpeech.say('All clear')
		if (bandContent > 0):
			bandMessage = content[bandContent + 20:bandContent + 52]
			buzz = bandMessage[2:4]
			command = bandMessage[12:14]
			fallMode = bandMessage[14:16]
			if command == '64':
				print 'Fall mode change ',  fallMode
				BandFallMode = fallMode
			if buzz != '00':
				print 'Buzz'
				textToSpeech.say('Buzz')
		textToSpeech.runAndWait() # what does this do?
	except:
		print 'Connection exception error'
	# capture end time				
	# delay while waiting for command
	loopTime = time.time()
	keys = '00' # default keys off
	while True:
		# Wait for keypress or timeout
		if msvcrt.kbhit():
			inp = msvcrt.getch()
			if inp == 'a':
				keys = '05' # code for both keys
			elif inp == 'c':
				keys = '04' # code for single key
			elif inp == 's':	
				sendShock = 'true'
			else:
				#print 'Test ended. Total message count ', packetCount, '. Average time ', totalTime/packetCount, '. Max & min time ', maxResponseTime ,minResponseTime
				print "Test ended. Total message count %d. Average time %.2f. Min %.2f max %.2f" %(packetCount, totalTime/packetCount, minResponseTime,maxResponseTime) 
				sys.exit(1) #exit
			break
		elif time.time() - loopTime > timeout:
			break
		#time.sleep(0.5) # Don't be a process hog.
		time.sleep(0.1) # Don't be a process hog.


