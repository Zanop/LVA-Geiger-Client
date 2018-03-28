from tkinter import *
import serial
import serial.tools.list_ports
import re
import time

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

def getReelog():
  if ser.is_open:
    ser.write("SILENT\n".encode('ascii'))
    # wait for possible "CPS, 0, CPM, 34, uSv/hr, 0.19, SLOW" in transit 
    # ~35-40 chars@1ms per char (9600bps)
    time.sleep(0.04)
    ser.reset_input_buffer()
    ser.write("SILENT\n".encode('ascii'))
    response = ser.readline().decode('ascii')
    #if response != 'OK\r\n' and re.match('CPS', response) is None:
    if response != 'OK\r\n':
      consolePrint("Error switching to SILENT {}".format(response), nl=True)
      return False
    # Clear the buffer from reports
    ser.reset_input_buffer()
    ser.write("REELOG\n".encode('ascii'))
    line1 = ser.readline()
    line2 = ser.readline()
    #consolePrint(line1.decode('ascii'))
    #consolePrint(line2.decode('ascii'))
    logmeta = line1.decode('ascii').rstrip().split(',')
    logdata = line2.decode('ascii').rstrip().split(',')
    consolePrint({'logmeta': logmeta, 'logdata': logdata}, nl=True)
    ser.write('NOISY\n'.encode('ascii'))
  return({'logmeta': logmeta, 'logdata': logdata })
  
# Scroll the console at the bottom
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
  logButton = Button(topFrame, text="Readlog", command=getReelog)
  logButton.grid(row=0, column=4)

  doseLabel = Label(mainFrame, textvariable = reading, font=('Times', '24'))
  doseLabel.pack(fill="x")

  comText = Text(bottomFrame, state='normal', width=80, height=20, bg="black", fg="lightgray")
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
