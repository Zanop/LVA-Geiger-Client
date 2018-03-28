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
    # clear coms 
    ser.write("SILENT\n".encode('ascii'))
    # wait for possible "CPS, 0, CPM, 34, uSv/hr, 0.19, SLOW" in transit 
    # ~35-40 chars@1ms per char (9600bps)
    time.sleep(0.04)
    ser.reset_input_buffer()
    ser.write("SILENT\n".encode('ascii'))
    response = ser.readline().decode('ascii')
    if response != 'OK\r\n':
      consolePrint("Error switching to SILENT {}".format(response), nl=True)
      return False
    # Clear the buffer from reports
    ser.reset_input_buffer()
    ser.write("REELOG\n".encode('ascii'))
    line1 = ser.readline()
    line2 = ser.readline()

    logmeta = line1.decode('ascii').rstrip().split(',')
    logdata = line2.decode('ascii').rstrip().split(',')
    # need data validity check here
    consolePrint({'logmeta': logmeta, 'logdata': logdata}, nl=True)
    ser.write('NOISY\n'.encode('ascii'))
  return({'logmeta': logmeta, 'logdata': logdata })
  
def getInfo():
  if ser.is_open:
    info = {}
    # clear coms 
    ser.write("SILENT\n".encode('ascii'))
    # wait for possible "CPS, 0, CPM, 34, uSv/hr, 0.19, SLOW" in transit 
    # ~35-40 chars@1ms per char (9600bps)
    time.sleep(0.04)
    ser.reset_input_buffer()
    ser.write("SILENT\n".encode('ascii'))
    response = ser.readline().decode('ascii')
    if response != 'OK\r\n':
      consolePrint("Error switching to SILENT {}".format(response), nl=True)
      return False
    # Clear the buffer from reports
    ser.reset_input_buffer()
    # get Firmware/Protocol
    ser.write("HELO\n".encode('ascii'))
    line1 = ser.readline()
    infoline = line1.decode('ascii').rstrip().split(',')
    
    info['firmware'] = infoline[1]
    info['protocol_version'] = infoline[2]
    
    # Clear the buffer from reports
    ser.reset_input_buffer()
    # get current status
    ser.write("STATUS\n".encode('ascii'))
    line1 = ser.readline()
    infoline = line1.decode('ascii').rstrip().split(',')
    
    '''
    Resolution is a power of two thing, specifying what time range
    each sample encompasses: "range = (15 * 2^res) seconds".
    Lowest resolution possible is 1 (30 seconds per sample).
    Highest resolution is not bounded in code, but because of the
    exponential nature of the resolution, it is unlikely that you'd
    ever encounter more than 15 (which equals 5d 16h per sample, or
    more than 22 months of logging).
    
    The SRAM and EEPROM log are different only in the first 20 minutes
    of uptime. After that their IDs are equal (the EEPROM one becomes
    what the SRAM one was), and the SRAM log is no longer updated.
    '''
    info['battery_milivolts'] = infoline[0]
    info['uptime_seconds'] = infoline[1]
    info['eeprom_log_id'] = infoline[2]
    info['eeprom_log_number_of_samples'] = infoline[3]
    info['eeprom_log_resolution'] = infoline[4]
    info['sram_log_id'] = infoline[5]
    info['sram_log_number_of_samples'] = infoline[6]
    
    # Clear the buffer from reports
    ser.reset_input_buffer()
    # get Device ID
    ser.write("GETID\n".encode('ascii'))
    line1 = ser.readline()
    infoline = line1.decode('ascii').rstrip().split(',')
    
    info['device_id'] = infoline[0]
    
    # Clear the buffer from reports
    ser.reset_input_buffer()
    # get Tube Multiplier
    ser.write("GETTM\n".encode('ascii'))
    line1 = ser.readline()
    infoline = line1.decode('ascii').rstrip().split(',')
    '''
    Synopsis: This is the tube sensitivity conversion factor. If you have
    X counts per minute, and the sensitiity is (N/D), the radiation
    would be calculated as ((X * N) / (D * 100)) uSv/h.

    Note:     The original geiger counter assumed this factor to be 57/100, or
    0.57, for the SBM-20 tube. What we introduced here is the same
    rational arithmetics (in order to avoid floating-point), but the
    numerator and especially the denominator are no longer hard-coded.
    This provides for easily achieving very high precision without
    comlpicating runtime computations on the device too much.

    Example:  If you run the geiger tube through calibration and it turns out
    that the actual sensitivity was 0.5617, you can approximate that
    sufficiently with 91/162.
    '''
    info['tube_multiplier'] = infoline[0]
    
    # Clear the buffer from reports
    ser.reset_input_buffer()
    # get radiation level alarm threshold, in uSv/h.
    ser.write("GETRA\n".encode('ascii'))
    line1 = ser.readline()
    infoline = line1.decode('ascii').rstrip().split(',')
    
    info['radiation_level_alarm'] = infoline[0]
    
    # Clear the buffer from reports
    ser.reset_input_buffer()
    # get the accumulated dose alarm threshold, in units of 10*uSv.
    ser.write("GETDA\n".encode('ascii'))
    line1 = ser.readline()
    infoline = line1.decode('ascii').rstrip().split(',')
    
    info['accumulated_dose_alarm'] = infoline[0]
    
    
    # need data validity check here
    consolePrint(info, nl=True)
    ser.write('NOISY\n'.encode('ascii'))
  return(info)
  
# Scroll the console at the bottom
def showEnd(event):
  comText.see(END)
  comText.edit_modified(0) #IMPORTANT - or <<Modified>> will not be called later.

if __name__ == "__main__":
  CPS="1"
  CPM="34"
  uSvh="0.14"
  Algo="SLOW"
  topFrame = Frame(root)
  mainFrame = Frame(root)
  bottomFrame = Frame(root)
  topFrame.pack(side="top", fill="x")
  mainFrame.pack(fill="x")
  bottomFrame.pack(side="bottom", fill="x")
  gaugeFrame = LabelFrame(mainFrame, text="Dose", labelanchor="nw")
  infoFrame = LabelFrame(mainFrame, text="Device Info", labelanchor="nw")
  gaugeFrame.grid(row=0, column=0, padx=5, pady=5, sticky=N+S+W+E)
  infoFrame.grid(row=0, column=1, padx=5, pady=5, sticky=N+E+S)

  

  comLabel = Label(topFrame, text="Com")
  comLabel.grid(row=0)
  comStatusLabel = Label(topFrame, text="COM", fg="red", textvariable=comStatus)
  comStatusLabel.grid(row=0, column=2)
  lvaStatusLabel = Label(topFrame, text="LVA", fg="red", textvariable=lvaStatus)
  lvaStatusLabel.grid(row=0, column=3)
  logButton = Button(topFrame, text="Readlog", command=getReelog)
  logButton.grid(row=0, column=4)


  #doseLabel = Label(gaugeFrame, textvariable = reading, font=('Times', '24'))
  #doseLabel.grid(row=0, column=0)
  infoLabel = Label(infoFrame, text="FW: r336")
  infoLabel.grid(row=0, column=1)

  doseLabelCPSLabel = Label(gaugeFrame, text="CPS")
  doseLabelCPMLabel = Label(gaugeFrame, text="CPM")
  doseLabeluSvLabel = Label(gaugeFrame, text="uSv/h")
  doseLabelAlgoLabel = Label(gaugeFrame, text="Algo")
  doseLabelCPSValue = Label(gaugeFrame, text="--", textvariable=CPS, font=('Times','10'))
  doseLabelCPMValue = Label(gaugeFrame, text="00", textvariable=CPM, font=('Times','28'))
  doseLabeluSvValue = Label(gaugeFrame, text="---", textvariable=uSvh, font=('Times','10'))
  doseLabelAlgoValue = Label(gaugeFrame, text="SLOW", textvariable=Algo, font=('Times','10'))
  doseLabelCPSLabel.grid(row=0, column=0, rowspan=1, columnspan=1, padx=3, pady=3, sticky=N+W)
  doseLabelCPMLabel.grid(row=1, column=0, rowspan=2, columnspan=2, padx=3, pady=3, sticky=N+W)
  doseLabeluSvLabel.grid(row=0, column=3, rowspan=1, columnspan=1, padx=3, pady=3, sticky=E)
  doseLabelAlgoLabel.grid(row=2, column=4, rowspan=1, columnspan=1, padx=3, pady=3, sticky=S+E)
  doseLabelCPSValue.grid(row=0, column=1, rowspan=1, columnspan=1, padx=3, pady=3, sticky=N+W)
  doseLabelCPMValue.grid(row=1, column=1, rowspan=3, columnspan=3, padx=3, pady=3, sticky=S+E+N)
  doseLabeluSvValue.grid(row=0, column=4, rowspan=1, columnspan=1, padx=3, pady=3, sticky=N+W)
  doseLabelAlgoValue.grid(row=3, column=4, rowspan=1, columnspan=1, padx=3, pady=3, sticky=S+E)


  comText = Text(bottomFrame, state='normal', width=60, height=20, bg="black", fg="lightgray")
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
