from tkinter import *
import serial
import serial.tools.list_ports
import re

root = Tk()
root.winfo_toplevel().title("Geiger Counter")
reading = StringVar()
comStatus = StringVar()
lvaStatus = StringVar()
comStatus.set("COM")
lvaStatus.set("LVA")
reading.set("CPS: -, CPM: --, --- uSv/h")

def comsSelect(event):
	comText.configure(state='normal')
	comText.insert(END,"Selected: "+coms[cv.get()])
	if ser.port != coms[cv.get()]:
		ser.close()
		ser.port = coms[cv.get()]
		ser.open()
		if ser.is_open:
			comText.insert(END," Port open!")
			comStatus.set('COM')
			comStatusLabel.config(fg="green")
		else:
				comText.insert(END," Couldn't open the port")
				comStatus.set('COM')
				comStatusLabel.config(fg="red")
		# Search for lva geiger
		line = ser.readline()
		pattern = re.compile("CPS, \d+, CPM, \d+, uSv/hr,")
		ok = pattern.match(line.decode('ascii'))
		if ok != None:
			comText.insert(END," Found LVA Geiger!")
			lvaStatus.set("LVA")
			lvaStatusLabel.config(fg="green")
		else:
			comText.insert(END," LVA Geiger not found.")
			lvaStatus.set("LVA")
			lvaStatusLabel.config(fg="red")
		ser.timeout=0.09
	else:
		comText.insert(END, "Port already selected!")
	comText.insert(END, "\n")
	comText.configure(state='disabled')

def getComPorts():
	comlist = {}
	coms = serial.tools.list_ports.comports()
	for com in coms:
		comText.configure(state='normal')
		#comText.insert(END, com.description+ "\n")
		#comText.configure(state='disabled')
		#comlist[com['name']]=com['device']
		comlist[com.description]=com.device
	return(comlist)

def readSerial():
	root.after(1000, readSerial)
	if ser.is_open:
		line = ser.readline()
		ser.reset_input_buffer()
		sline = line.decode('ascii').rstrip()
		pattern = re.compile("CPS, (\d+), CPM, (\d+), uSv/hr, ([\d\.]+), (\w+)")
		m = pattern.match(sline)
		if m != None:
			comText.configure(state='normal')
			#comText.insert(END, sline + "\n" + m.group(3))
			reading.set(sline)
			comText.insert(END, sline + "\n")
			comText.configure(state='disabled')
		
	pass
	
def showEnd(event):
	comText.see(END)
	comText.edit_modified(0) #IMPORTANT - or <<Modified>> will not be called later.


if __name__ == "__main__":
	topFrame = Frame(root)
	mainFrame = Frame(root)
	bottomFrame = Frame(root)
	topFrame.pack(side="top", fill="x")
	mainFrame.pack(fill="x")
	bottomFrame.pack(side="bottom", fill="x")

	comLabel = Label(topFrame, text="Com")
	comLabel.grid(row=0)
	comStatusLabel = Label(topFrame, text="COM", fg="red", textvariable=comStatus)
	comStatusLabel.grid(row=0, column=2)
	lvaStatusLabel = Label(topFrame, text="LVA", fg="red", textvariable=lvaStatus)
	lvaStatusLabel.grid(row=0, column=3)

	doseLabel = Label(mainFrame, textvariable = reading, font=('Times', '24'))
	doseLabel.pack(fill="x")

	comText = Text(bottomFrame, state='normal', width=60, height=5, bg="black", fg="lightgray")
	comText.bind('<<Modified>>',showEnd)
	comText.pack()

	# Get list of available com ports
	#coms = serial.tools.list_ports.comports()
	coms = getComPorts()
	cv = StringVar()
	cv.set(next(iter(coms)))
	comlist = OptionMenu(topFrame, cv, *coms, command=comsSelect)
	comlist.grid(row=0, column=1)

	ser = serial.Serial()
	ser.baudrate = 9600
	ser.port = coms[cv.get()]
	root.after(1000, readSerial)
	root.mainloop()