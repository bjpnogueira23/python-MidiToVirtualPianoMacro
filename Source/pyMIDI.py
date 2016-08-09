import os

class MidiTrackEvent:
	type = -1
	channel = -1
	
	typeDict = {0x8 : "Key Release",
				0x9 : "Key Press",
				0xA : "AfterTouch",
				0xB : "Pedal",
				0xC : "Instrument Change",
				0xD : "Global AfterTouch",
				0xE : "Pitch Bend"
				}
				
	typeBytes = {	0x8 : 2,
					0x9 : 2,
					0xA : 2,
					0xB : 2,
					0xC : 1,
					0xD : 1,
					0xE : 2
				}

class MidiMetaEvent:
	offset = -1
	type = -1
	length = -1
	bytes = -1

	def __init__(self,offset,type,length,bytes):
		self.offset = offset
		self.type = type
		self.length = length
		self.bytes = bytes

class MidiFile:
	bytes = -1
	headerLength = -1
	headerOffset = 23
	format = -1
	tracks = -1
	division = -1
	divisionType = -1
	itr = 0
	runningStatus = -1
	
	midiRecord = open("midiRecord.txt","w")
	midiSong = open("song.txt","w")
	
	virtualPianoScale = "1!2@34$5%6^78*9(0qQwWeErtTyYuiIoOpPasSdDfgGhHjJklLzZxcCvVbBnm"
	
	deltaTimeStarted = False
	deltaTime = 0
	
	runningStatusSet = False
	startSequence = [ 	[0x4D,0x54,0x68,0x64], #MThd
						[0x4D,0x54,0x72,0x6B], #MTrk
						[0xFF] #FF
					]
	startCounter = [0] * len(startSequence)
	
	events = []
	notes = []
	
	typeDict = {0x00 : "Sequence Number",
				0x01 : "Text Event",
				0x02 : "Copyright Notice",
				0x03 : "Sequence/Track Name",
				0x04 : "Instrument Name",
				0x05 : "Lyric",
				0x06 : "Marker",
				0x07 : "Cue Point",
				0x20 : "MIDI Channel Prefix",
				0x2F : "End of Track",
				0x51 : "Set Tempo",
				0x54 : "SMTPE Offset",
				0x58 : "Time Signature",
				0x59 : "Key Signature",
				0x7F : "Sequencer-Specific Meta-event",
				0x21 : "Prefix Port",
				0x20 : "Prefix Channel",
				0x09 : "Other text format"
				}

	
	def __init__(self,filename):
		self.midiSong.write("tempo= 180\n")
		f = open(filename,"rb")
		self.bytes = bytearray(f.read())
		self.readEvents()
	
	def checkStartSequence(self):
		for i in range(len(self.startSequence)):
			if(len(self.startSequence[i]) == self.startCounter[i]):
				#print("Found start sequence",self.startSequence[i])
				return True
		return False
	
	def skip(self,i):
		self.itr += i
	
	def readLength(self):
		contFlag = True
		length = 0
		while(contFlag):
			if((self.bytes[self.itr] & 0x80) >> 7 == 0x1):
				length = (length << 7) + (self.bytes[self.itr] & 0x7F)
			else:
				contFlag = False
				length = (length << 7) + (self.bytes[self.itr] & 0x7F)
			self.itr += 1
		return length
	
	def readMTrk(self):
		length = self.getInt(4)
		self.log("MTrk len",length)
		self.readMidiTrackEvent(length)
	
	def readMThd(self):
		self.headerLength = self.getInt(4)
		self.log("HeaderLength",self.headerLength)
		self.format = self.getInt(2)
		self.tracks = self.getInt(2)
		div = self.getInt(2)
		self.divisionType = (div & 0x8000) >> 16
		self.division = div & 0x7FFF
		self.log("Format %d\nTracks %d\nDivisionType %d\nDivision %d" % (self.format,self.tracks,self.divisionType,self.division))
	
	def readText(self,length):
		s = ""
		start = self.itr
		while(self.itr < length+start):
			s += chr(self.bytes[self.itr])
			self.itr+=1
		return s
	
	def readMidiMetaEvent(self,deltaT):
		type = self.bytes[self.itr]
		self.itr+=1
		length = self.readLength()
		self.log("MIDIMETAEVENT",self.typeDict[type],"LENGTH",length,"DT",deltaT)
		if(type == 0x2F):
			self.log("END TRACK")
			self.itr += 2
			return False
		else:
			if(type in [0x01,0x02,0x03,0x04,0x05,0x06,0x07]):
				self.log("\t",self.readText(length))
			else:
				self.itr+= length
			return True
		
	def readMidiTrackEvent(self,length):
		self.log("TRACKEVENT")
		self.deltaTime = 0
		start = self.itr
		continueFlag = True
		while(length > self.itr - start and continueFlag):
			deltaT= self.readLength()
			self.deltaTime += deltaT
			if(self.bytes[self.itr] == 0xFF):
				self.itr+= 1
				continueFlag = self.readMidiMetaEvent(deltaT)
			elif(self.bytes[self.itr] >= 0xF0 and self.bytes[self.itr] <= 0xF7):
				self.runningStatusSet = False
				self.runningStatus = -1
				self.log("RUNNING STATUS SET:","CLEARED")
			else:
				self.readVoiceEvent(deltaT)
		self.log("End of MTrk event, jumping from",self.itr,"to",start+length)
		self.itr = start+length
				
	def readVoiceEvent(self,deltaT):
		if(self.bytes[self.itr] < 0x80 and self.runningStatusSet):
			type = self.runningStatus
			channel = type & 0x0F
		else:
			type = self.bytes[self.itr]
			channel = self.bytes[self.itr] & 0x0F
			if(type >= 0x80 and type <= 0xF7):
				self.log("RUNNING STATUS SET:",hex(type))
				self.runningStatus = type
				self.runningStatusSet = True
			self.itr += 1
		
		if(type >> 4 == 0x9):
			key = self.bytes[self.itr]
			self.itr += 1
			velocity = self.bytes[self.itr]
			self.itr += 1
			
			
			self.log(self.deltaTime/self.division,self.virtualPianoScale[key-23-13])
			if(velocity > 0):
				self.notes.append([(self.deltaTime/self.division),self.virtualPianoScale[key-23-12]])
				#self.midiSong.write(str(self.deltaTime/self.division)+ " " + self.virtualPianoScale[key-23-12] +"\n")
			#print(deltaT,channel,key,velocity)
		elif(not type >> 4 in [0x8,0x9,0xA,0xB,0xD,0xE]):
			self.log("VoiceEvent",hex(type),hex(self.bytes[self.itr]),"DT",deltaT)
			self.itr +=1
		else:
			self.log("VoiceEvent",hex(type),hex(self.bytes[self.itr]),hex(self.bytes[self.itr+1]),"DT",deltaT)
			self.itr+=2
	
	def readEvents(self):
		while(self.itr+1 < len(self.bytes)):
			#Reset counters to 0
			for i in range(len(self.startCounter)):
				self.startCounter[i] = 0
				
			#Get to next event / MThd / MTrk
			while(self.itr+1 < len(self.bytes) and not self.checkStartSequence()):
				for i in range(len(self.startSequence)):
					if(self.bytes[self.itr] == self.startSequence[i][self.startCounter[i]]):
						self.startCounter[i] += 1
					else:
						self.startCounter[i] = 0
						
				if(self.itr+1 < len(self.bytes)):
					self.itr += 1
						
				if(self.startCounter[0] == 4):
					self.readMThd()
				elif(self.startCounter[1] == 4):
					self.readMTrk()
	
	def log(self,*arg):
		for s in range(len(arg)):
			self.midiRecord.write(str(arg[s]) + " ")
		self.midiRecord.write("\n")
	
	def getInt(self,i):
		k = 0
		for n in self.bytes[self.itr:self.itr+i]:
			k = (k << 8) + n
		self.itr += i
		return k

fileList = os.listdir()
midList = []
for f in fileList:
	if(".mid" in f):
		midList.append(f)
print("Press letter of midi file to process")
for i in range(len(midList)):
	print(chr(97+i),":",midList[i])

choice = input()
print("Processing",midList[ord(choice)-97])
midi = MidiFile(midList[ord(choice)-97])
midi.notes.sort()

for l in midi.notes:
	midi.midiSong.write(str(l[0]) + " " + str(l[1]) + "\n")