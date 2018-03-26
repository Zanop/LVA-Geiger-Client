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

# detect if this is lva geiger output
def isLva(sline):
  pattern = re.compile("CPS, \d+, CPM, \d+, uSv/hr,")
  ok = pattern.match(sline)
  if ok != None:
    return True
  else:
    return False

# print line in the text console
def consolePrint(text, nl=False):
  comText.configure(state='normal')
  comText.insert(END, text)
  if nl:
    comText.insert(END, "\n")
  comText.configure(state='disabled')

def comsSelect(event):
  consolePrint("Selected: "+coms[cv.get()])
  if ser.port != coms[cv.get()]:
    ser.close()
    ser.port = coms[cv.get()]
    ser.open()
    if ser.is_open:
      consolePrint(" Port open!")
      comStatus.set('COM')
      comStatusLabel.config(fg="green")
    else:
        consolePrint(" Couldn't open the port")
        comStatus.set('COM')
        comStatusLabel.config(fg="red")
    # Search for lva geiger
    ser.timeout=0.09
  else:
    consolePrint("Port already selected!")
  consolePrint("", nl=True)
  

def getComPorts():
  comlist = {}
  coms = serial.tools.list_ports.comports()
  for com in coms:
    comlist[com.description]=com.device
  return(comlist)

def readSerial():
  root.after(1000, readSerial)
  if ser.is_open:
    line = ser.readline()
    if isLva(line.decode('ascii')):
      lvaStatus.set("LVA")
      lvaStatusLabel.config(fg="green")
    else:
      lvaStatus.set("LVA")
      lvaStatusLabel.config(fg="red")
    ser.reset_input_buffer()
    sline = line.decode('ascii').rstrip()
    pattern = re.compile("CPS, (\d+), CPM, (\d+), uSv/hr, ([\d\.]+), (\w+)")
    m = pattern.match(sline)
    if m != None:
      #consolePrint(sline + "\n" + m.group(3))
      reading.set(sline)
      consolePrint(sline, nl=True)    
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

  ser = serial.Serial(timeout=1)
  ser.baudrate = 9600
  ser.port = coms[cv.get()]
  root.after(1000, readSerial)
  root.mainloop()
