#!/usr/bin/env python

#  Copyright 2010 Randolph C Voorhies
#  http://ilab.usc.edu/~rand
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.    If not, see <http://www.gnu.org/licenses/>.

import wx
import wx.combo

import serial
import threading
import time
import os
from threading    import Thread
from serial.tools import list_ports
from collections  import OrderedDict

class Style:
    def __init__(self):
        self.rx = wx.TextAttr(colText = wx.Colour(100, 0, 0))
        self.tx = wx.TextAttr(colText = wx.Colour(0, 0, 100))
style = Style()

rxStyle = wx.TextAttr(
    colText = wx.Colour(100, 0, 0)
)
txStyle = wx.TextAttr(
    colText = wx.Colour(0, 0, 100)
)

parityMap = {
    'None':    serial.PARITY_NONE,
    'Even':    serial.PARITY_EVEN,
    'Odd':     serial.PARITY_ODD,
}

stopMap = {
    '1':   serial.STOPBITS_ONE,
    '1.5': serial.STOPBITS_ONE_POINT_FIVE,
    '2':   serial.STOPBITS_TWO
}

bytesizeMap = {
    '5': serial.FIVEBITS,
    '6': serial.SIXBITS,
    '7': serial.SEVENBITS,
    '8': serial.EIGHTBITS
}


class randtermFrame(wx.Frame, Thread):
    ##################################################
    def __init__(self, parent, title):
        Thread.__init__(self)
        wx.Frame.__init__(self, parent, title=title, size=(600, 400))

        self.cfg = wx.Config('randtermrc')

        self.historyLock = threading.Lock()
        self.history = []

        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)

        self.CreateStatusBar()
        
        # File Menu
        fileMenu = wx.Menu()
        menuAbout = fileMenu.Append(wx.ID_ABOUT, "&About",
                                    " Information about randterm")
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        menuExit = fileMenu.Append(wx.ID_EXIT, "E&xit", " Exit")
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)

#         # Connect Menu
#         self.connectMenu = wx.Menu()
#         ## Port Selection
#         self.setPort = self.connectMenu.Append(wx.ID_ANY, 'Set Port...')
#         self.Bind(wx.EVT_MENU, self.OnSetPort, self.setPort)
#         self.connectMenu.AppendSeparator()
#         self.portName = ""
#         ## Baud SubMenu
#         self.baudRadios = []
#         self.baudMenu = wx.Menu()
#         self.baudRadios.append(self.baudMenu.AppendRadioItem(wx.ID_ANY, '2400'))
#         self.baudRadios.append(self.baudMenu.AppendRadioItem(wx.ID_ANY, '4800'))
#         self.baudRadios.append(self.baudMenu.AppendRadioItem(wx.ID_ANY, '9600'))
#         self.baudRadios.append(self.baudMenu.AppendRadioItem(wx.ID_ANY, '19200'))
#         self.baudRadios.append(self.baudMenu.AppendRadioItem(wx.ID_ANY, '38400'))
#         self.baudRadios.append(self.baudMenu.AppendRadioItem(wx.ID_ANY, '57600'))
#         self.baudRadios.append(self.baudMenu.AppendRadioItem(wx.ID_ANY, '115200'))
#         self.baudRadios.append(self.baudMenu.AppendRadioItem(wx.ID_ANY, '312500'))
#         self.connectMenu.AppendMenu(wx.ID_ANY, 'Baud Rate',         self.baudMenu)
#         ## Parity SubMenu
#         self.parityRadios = []
#         self.parityMenu = wx.Menu()
#         for k,v in parityMap.items():
#             self.parityRadios.append(self.parityMenu.AppendRadioItem(wx.ID_ANY, k))
#         self.connectMenu.AppendMenu(wx.ID_ANY, 'Parity',                self.parityMenu)
#         ## Byte Size SubMenu
#         self.byteRadios = []
#         self.byteMenu = wx.Menu()
#         for k,v in bytesizeMap.items():
#             self.byteRadios.append(self.byteMenu.AppendRadioItem(wx.ID_ANY, k))
#         self.connectMenu.AppendMenu(wx.ID_ANY, 'Byte Size',         self.byteMenu)
#         ## Stop Bits SubMenu
#         self.stopbitsRadios = []
#         self.stopbitsMenu = wx.Menu()
#         for k,v in stopMap.items():
#             self.stopbitsRadios.append(self.stopbitsMenu.AppendRadioItem(wx.ID_ANY, k))
#         self.connectMenu.AppendMenu(wx.ID_ANY, 'Stop Bits',         self.stopbitsMenu)
#         ## Flow Control SubMenu
#         self.flowMenu = wx.Menu()
#         self.xonoffCheck = self.flowMenu.AppendCheckItem(wx.ID_ANY, 'Xon/Xoff')
#         self.rtsctsCheck = self.flowMenu.AppendCheckItem(wx.ID_ANY, 'RTS/CTS')
#         self.dsrdtrCheck = self.flowMenu.AppendCheckItem(wx.ID_ANY, 'DSR/DTR')
#         self.connectMenu.AppendMenu(wx.ID_ANY, 'Flow Control',    self.flowMenu)
#         ## Open Connection Item
#         self.connectMenu.AppendSeparator()
#         openConnection    = self.connectMenu.Append(
#             wx.ID_ANY, '&Open Connection', 'Open Connection')
#         self.Bind(wx.EVT_MENU, self.OnSetConnection, openConnection)
#         closeConnection = self.connectMenu.Append(
#             wx.ID_ANY, '&Close Connection', 'Close Connection')
#         self.Bind(wx.EVT_MENU, self.OnCloseConnection, closeConnection)
        
        
        # Menu Bar
        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu,        "&File")
#         menuBar.Append(self.connectMenu, "&Connect")
        self.SetMenuBar(menuBar)

        # Setup the defaults
        self.readDefaults()

        # Main Window
        self.leftLayout = wx.BoxSizer(wx.VERTICAL)

        class SerialPort:
            def __init__(self, parent):
                self.parent = parent
                self.sizer = wx.GridBagSizer(5, 5)
                self.sizer.AddGrowableCol(0)
                self.sizer.AddGrowableCol(1)
                self.sizer.AddGrowableCol(2)
                self.sizer.AddGrowableCol(3)
                self.sizer.AddGrowableCol(4)
                self.sizer.AddGrowableCol(5)
                self.sizer.AddGrowableCol(7)
                
                class Base():
                    def __init__(self, parent, name, choices, editable = True):
                        self.parent = parent
#                         choices = sorted(choices)
#                         choices.sort(key=int)
                        self.name = wx.StaticText(parent, label = name)
                        if editable == True:
                            self.values = wx.ComboBox(parent, choices = choices)
                        else: 
                            self.values = wx.ComboBox(parent, choices = choices, style = wx.CB_READONLY)
                        dc = wx.ClientDC(parent)
                        if choices != []:
                            self.values.SetValue(choices[0])
                            tsize = max((dc.GetTextExtent (c)[0] for c in choices)) 
                            self.values.SetMinSize((tsize + 50, -1))
                        else:
                            self.values.SetMinSize((50, -1))
              
                # serial port
                class PortPath(Base):
                    def __init__(self, parent):
                        self.parent = parent
                        Base.__init__(self, parent, "Port Path", [], False)
#                         super(PortPath, self).__init__(parent, "Port Path", [''])
                        self.values.Bind(wx.EVT_COMBOBOX, self.OnListClick)

                    def OnListClick(self):
                        """
                        Returns a generator for all available serial ports
                        """
                        self.values.Clear()
                        # windows
                        if os.name == 'nt':
                            for i in range(256):
                                try:
                                    s = serial.Serial(i)
                                    s.close()
                                    self.values.Append('COM' + str(i + 1))
                                except serial.SerialException:
                                    pass
                        # unix
                        else:
                            for i in list_ports.comports():
                                    self.values.Append(str(i))

                self.portPath = PortPath(parent) 

                # baud rate
                class BaudRate(Base):
                    def __init__(self, parent):
                        self.parent = parent
                        self.map = OrderedDict({})
                        self.map[  '2400'] =   2400
                        self.map[  '4800'] =   4800
                        self.map[  '9600'] =   9600
                        self.map[ '19200'] =  19200
                        self.map[ '38400'] =  38400
                        self.map[ '57600'] =  57600
                        self.map['115200'] = 115200
                        self.map['312500'] = 312500 
                        self.map['Custom'] = None
                        Base.__init__(self, parent, "BaudRate", self.map.keys())
#                         super(BaudRate, self).__init__(parent, "BaudRate", self.map.keys())
                self.baudRate = BaudRate(parent) 

                # parity
                class Parity(Base):
                    def __init__(self, parent):
                        self.parent = parent
                        self.map = OrderedDict({})
                        self.map[ 'None'] = serial.PARITY_NONE
                        self.map[  'Odd'] = serial.PARITY_ODD
                        self.map[ 'Even'] = serial.PARITY_EVEN
                        self.map[ 'Mark'] = serial.PARITY_MARK
                        self.map['Space'] = serial.PARITY_SPACE
                        Base.__init__(self, parent, "Parity", self.map.keys())
#                         super(Parity, self).__init__(parent, "Parity", self.map.keys())
                self.parity = Parity(parent) 

                # word bits
                class Bits(Base):
                    def __init__(self, parent):
                        self.parent = parent
                        self.map = OrderedDict({})
                        self.map['5'] = serial.FIVEBITS
                        self.map['6'] = serial.SIXBITS
                        self.map['7'] = serial.SEVENBITS
                        self.map['8'] = serial.EIGHTBITS
                        Base.__init__(self, parent, "Word bits", self.map.keys())
#                         super(Bits, self).__init__(parent, "Word bits", self.map.keys())
                self.wordBits = Bits(parent) 

                # stop bits
                class StopBits(Base):
                    def __init__(self, parent):
                        self.parent = parent
                        self.map = OrderedDict({})
                        self.map['1']   = serial.STOPBITS_ONE
                        self.map['1.5'] = serial.STOPBITS_ONE_POINT_FIVE
                        self.map['2']   = serial.STOPBITS_TWO
                        Base.__init__(self, parent, "Stop bits", self.map.keys())
#                         super(StopBits, self).__init__(parent, "Stop bits", self.map.keys())
                self.stopBits = StopBits(parent) 

                # flow control
                class FlowControl(Base):
                    def __init__(self, parent):
                        self.parent = parent
                        self.map = ['None', 'Xon/Xoff', 'RTS/CTS', 'DSR/DTR']
                        Base.__init__(self, parent, "Flow control", self.map)
#                         super(FlowControl, self).__init__(parent, "Flow control", self.map.keys())
                self.flowControl = FlowControl(parent) 

                # connecting
                class Connector:
                    def __init__(self, parent):
                        self.parent = parent
                        self.toggle = wx.Button(parent, id = wx.ID_ANY, label = "Connect")
                        parent.Bind(wx.EVT_BUTTON, self.OnToggle, self.toggle)
                        self.isConnected = False

                    def OnToggle(self):
                        if(self.connected):
                            self.Close(None)
                        else:
                            self.Open(None)

                    def Open(self):
                        pass
#                         if self.portName == "":
#                             self.OnSetPort(None)
#                             return
#                  
#                         baudRadio     = None
#                         for b in self.baudRadios:     
#                             if b.IsChecked(): baudRadio     = b
#                         parityRadio = None
#                         for p in self.parityRadios:
#                             if p.IsChecked(): parityRadio = p
#                         byteRadio     = None
#                         for b in self.byteRadios:
#                             if b.IsChecked(): byteRadio     = b
#                         stopRadio     = None
#                         for s in self.stopbitsRadios:
#                             if s.IsChecked(): stopRadio     = s
#                 
#                         self.serialCon = serial.Serial()
#                         self.serialCon.port         = self.portName
#                         self.serialCon.baudrate = int(baudRadio.GetLabel())
#                         self.serialCon.bytesize = bytesizeMap[byteRadio.GetLabel()]
#                         self.serialCon.parity     = parityMap[parityRadio.GetLabel()]
#                         self.serialCon.stopbits = stopMap[stopRadio.GetLabel()]
#                         self.serialCon.xonxoff    = self.xonoffCheck.IsChecked()
#                         self.serialCon.rtscts     = self.rtsctsCheck.IsChecked()
#                         self.serialCon.dsrdtr     = self.dsrdtrCheck.IsChecked()
#                         self.serialCon.timeout    = .3
#                 
#                         self.cfg.Write('portname', self.portName)
#                         self.cfg.Write('baud',         baudRadio.GetLabel())
#                         self.cfg.Write('parity',     parityRadio.GetLabel())
#                         self.cfg.Write('bytesize', byteRadio.GetLabel())
#                         self.cfg.Write('stopbits', stopRadio.GetLabel())
#                         for item in self.flowMenu.GetMenuItems():
#                             self.cfg.WriteBool(item.GetLabel(),item.IsChecked())
#                 
#                         try:
#                             self.serialCon.open()
#                         except serial.SerialException as ex:
#                             self.autoDisconnectCheck.SetValue(False)
#                             wx.MessageDialog(None, str(ex), 'Serial Error', wx.OK | wx.ICON_ERROR).ShowModal()
#                             self.SetStatusText('Not Connected...')
#                             self.connected = False
#                             return
#                 
#                         self.SetStatusText('Connected to ' + self.portName + ' ' + baudRadio.GetLabel() + 'bps')
#                         self.connected = True
#                         self.connectButton.SetBackgroundColour(wx.Colour(0, 255, 0))
#                         self.connectButton.SetLabel("Disconnect")
                self.connector = Connector(parent) 

                self.autoDisconnect = wx.CheckBox(parent, label = 'Auto disconnect')

                self.sizer.Add(self.portPath.name     , pos = (0, 0), flag = wx.LEFT|wx.TOP   |wx.EXPAND)
                self.sizer.Add(self.portPath.values   , pos = (1, 0), flag = wx.LEFT|wx.BOTTOM|wx.EXPAND)
                self.sizer.Add(self.baudRate.name     , pos = (0, 1), flag = wx.LEFT|wx.TOP   |wx.EXPAND)
                self.sizer.Add(self.baudRate.values   , pos = (1, 1), flag = wx.LEFT|wx.BOTTOM|wx.EXPAND)
                self.sizer.Add(self.parity.name       , pos = (0, 2), flag = wx.LEFT|wx.TOP   |wx.EXPAND)
                self.sizer.Add(self.parity.values     , pos = (1, 2), flag = wx.LEFT|wx.BOTTOM|wx.EXPAND)
                self.sizer.Add(self.wordBits.name     , pos = (0, 3), flag = wx.LEFT|wx.TOP   |wx.EXPAND)
                self.sizer.Add(self.wordBits.values   , pos = (1, 3), flag = wx.LEFT|wx.BOTTOM|wx.EXPAND)
                self.sizer.Add(self.stopBits.name     , pos = (0, 4), flag = wx.LEFT|wx.TOP   |wx.EXPAND)
                self.sizer.Add(self.stopBits.values   , pos = (1, 4), flag = wx.LEFT|wx.BOTTOM|wx.EXPAND)
                self.sizer.Add(self.flowControl.name  , pos = (0, 5), flag = wx.LEFT|wx.TOP   |wx.EXPAND)
                self.sizer.Add(self.flowControl.values, pos = (1, 5), flag = wx.LEFT|wx.BOTTOM|wx.EXPAND)
                self.sizer.Add(self.connector.toggle  , pos = (1, 6), flag = wx.LEFT|wx.BOTTOM|wx.EXPAND)
                self.sizer.Add(self.autoDisconnect    , pos = (1, 7), flag = wx.LEFT|wx.BOTTOM|wx.EXPAND)
                
        self.serialPort = SerialPort(self)
        self.leftLayout.Add(self.serialPort.sizer, 0, flag = wx.EXPAND | wx.ALL, border = 5)
        
        class Texter:
            def __init__(self, parent):
                self.parent = parent
                self.layout = wx.BoxSizer(wx.HORIZONTAL)
                
                class Asciier:
                    def __init__(self, parent):
                        self.parent = parent

                        self.head = wx.BoxSizer(wx.HORIZONTAL)
                        
                        self.clear = wx.Button(parent, id = wx.ID_ANY, label = "Clear")
                        self.head.Add(self.clear, 0, wx.CENTER)

                        self.enable = wx.CheckBox(parent, label = 'ASCII')
                        self.head.Add(self.enable, 0, wx.CENTER)
                        self.enable.SetMinSize((-1, 35))
                        
                        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
                        self.sheet  = wx.TextCtrl(parent, style = wx.TE_MULTILINE | wx.TE_READONLY)
                        self.sheet.SetFont(font)
                        
                        self.layout = wx.BoxSizer(wx.VERTICAL)
                        self.layout.Add(self.head, 0, wx.EXPAND | wx.CENTER)
                        self.layout.Add(self.sheet , 1, wx.EXPAND | wx.CENTER)
                self.asciier = Asciier(parent)
                self.layout.Add(self.asciier.layout, 6, wx.EXPAND | wx.CENTER)

                class Base:
                    def __init__(self, parent, desc, isEnabled, size):
                        self.parent = parent
                        self.enable = wx.CheckBox(parent, label = desc)
                        self.enable.SetMinSize(size)

                        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
                        self.sheet  = wx.TextCtrl(parent, style = wx.TE_MULTILINE | wx.TE_READONLY)
                        self.sheet.SetFont(font)
                        
                        self.layout = wx.BoxSizer(wx.VERTICAL)
                        self.layout.Add(self.enable, 0, wx.EXPAND | wx.CENTER)
                        self.layout.Add(self.sheet , 1, wx.EXPAND | wx.CENTER)
                
                class Decimaler(Base):
                    def __init__(self, parent, size):
                        self.parent = parent
                        Base.__init__(self, parent, 'Decimal', False, size)
                self.decimaler = Decimaler(parent, self.asciier.clear.GetSize())
                self.layout.Add(self.decimaler.layout, 1, wx.EXPAND | wx.CENTER)

                class Hexadecimaler(Base):
                    def __init__(self, parent, size):
                        self.parent = parent
                        Base.__init__(self, parent, 'Hex', False, size)
                self.hexadecimaler = Hexadecimaler(parent, self.asciier.clear.GetSize())
                self.layout.Add(self.hexadecimaler.layout, 1, wx.EXPAND | wx.CENTER)

                class Binarier(Base):
                    def __init__(self, parent, size):
                        self.parent = parent
                        Base.__init__(self, parent, 'Binary', False, size)
                self.binarier = Binarier(parent, self.asciier.clear.GetSize())
                self.layout.Add(self.binarier.layout, 1, wx.EXPAND | wx.CENTER)
                
        outputSizer = wx.BoxSizer(wx.VERTICAL)

        self.outer = Texter(self)
        outputSizer.Add(self.outer.layout, 2, wx.EXPAND | wx.CENTER)

        self.inner = Texter(self)
        outputSizer.Add(self.inner.layout, 1, wx.EXPAND | wx.CENTER)
        
        self.leftLayout.Add(outputSizer, 1, flag = wx.EXPAND | wx.ALL, border = 5)
        
        class Sender:
            def __init__(self, parent):
                self.parent = parent

                self.layout = wx.BoxSizer(wx.HORIZONTAL)

                formats = ['ASCII', 'HEX', 'DEC', 'BIN']
                self.format = wx.ComboBox(parent, choices = formats)
                self.format.SetValue(formats[0])
                dc = wx.ClientDC(parent)
                tsize = max((dc.GetTextExtent (c)[0] for c in formats)) 
                self.format.SetMinSize((tsize + 50, -1))
                self.layout.Add(self.format, 0, flag = wx.CENTER | wx.EXPAND)

                self.liveType   = wx.CheckBox(parent, label = 'Live Typing')
                self.layout.Add(self.liveType, 0, flag = wx.CENTER | wx.EXPAND)
                                                                     
                self.textLine   = wx.TextCtrl(parent)                
                self.layout.Add(self.textLine, 1, flag = wx.CENTER | wx.EXPAND)
                 
                self.terminator = []
                self.terminator.append(wx.CheckBox(parent, label = 'CR'))
                self.terminator.append(wx.CheckBox(parent, label = 'CR'))
                self.terminator.append(wx.CheckBox(parent, label = 'LF'))
                self.terminator.append(wx.CheckBox(parent, label = 'LF'))
                for i in range(len(self.terminator)):
                    self.layout.Add(self.terminator[i], 0, flag = wx.CENTER)
                    
                self.send = wx.Button(parent, id = wx.ID_ANY, label = "Send")
                self.layout.Add(self.send, 0, flag = wx.CENTER | wx.EXPAND)
        self.sender = Sender(self)
        self.leftLayout.Add(self.sender.layout, 0, flag = wx.CENTER | wx.EXPAND | wx.ALL, border = 5)

        self.mainLayout = wx.BoxSizer(wx.HORIZONTAL)
        self.mainLayout.Add(self.leftLayout    , 1, flag = wx.EXPAND | wx.ALL)

        # Serial Output Area
        ## Output Type
#         topSizer = wx.BoxSizer(wx.HORIZONTAL)
#         self.displayTypeRadios = wx.RadioBox(self, wx.ID_ANY,
#                                              style = wx.RA_HORIZONTAL, 
#                                              label="RX Format", 
#                                              choices = ('Ascii', 'Decimal', 
#                                                         'Hex', 'Binary'))
#         self.Bind(wx.EVT_RADIOBOX, self.OnChangeDisplay, self.displayTypeRadios)
#         topSizer.Add(self.displayTypeRadios, 0)
#         self.clearOutputButton = wx.Button(self, id=wx.ID_ANY, label="Clear")
#         self.Bind(wx.EVT_BUTTON, self.OnClearOutput, self.clearOutputButton)
#         topSizer.AddStretchSpacer()
#         topSizer.Add(self.clearOutputButton, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT )
#         outputSizer.Add(topSizer, flag=wx.EXPAND)
#         ## Output Area
#         serialFont = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
#         self.serialOutput = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
#         self.serialOutput.SetFont(serialFont)
#         outputSizer.Add(self.serialOutput, 1, wx.EXPAND)

        
        class  Scripter:
            def __init__(self, parent):
                self.parent = parent
                self.macrosPerCol = 15
                self.cols         = 3
                self.sizer = wx.GridBagSizer(0, 0)
                for i in range(self.macrosPerCol):
                    self.sizer.AddGrowableRow(i)
                
                class Base:
                    def __init__(self, parent, desc):
                        self.parent = parent
                        self.trigger = wx.Button(parent, id = wx.ID_ANY, label = desc)
                    
                    def SetName(self):
                        pass
                        
                    def SetExec(self):
                        pass
                        
                self.macro = []
                for i in range(0, self.macrosPerCol * self.cols):
                    desc  = 'm' + str(i + 1) 
                    self.macro.append(Base(parent, desc))
                    self.sizer.Add(self.macro[i].trigger, pos = (i / self.cols, i % self.cols), flag = wx.EXPAND | wx.ALL)
                                       
        self.scripter = Scripter(self)
        self.mainLayout.Add(self.scripter.sizer, 0, flag = wx.EXPAND | wx.ALL)
        
#         # Input Area
#         lowerAreaSizer = wx.BoxSizer(wx.VERTICAL)
#         ## LiveType
#         liveTypeSizer = wx.BoxSizer(wx.HORIZONTAL)
#         lowerAreaSizer.Add(liveTypeSizer)
#         liveTypeSizer.Add(wx.StaticText(self, wx.ID_ANY, " LiveType: "))
#         self.liveType = wx.TextCtrl(self, wx.ID_ANY, '',
#                                     style=wx.TE_LEFT|wx.TE_MULTILINE|wx.TE_RICH, size=(160,25))
#         liveTypeSizer.Add(self.liveType)
#         self.Bind(wx.EVT_TEXT, self.OnSendLiveType, self.liveType)
#         ## Input Array
#         lowerAreaSizer2 = wx.BoxSizer(wx.HORIZONTAL)
#         lowerAreaSizer.Add(lowerAreaSizer2)
#         inputAreasSizer = wx.BoxSizer(wx.VERTICAL)
#         lowerAreaSizer2.Add(inputAreasSizer)
#         formatTypes = ['Ascii', 'Decimal', 'Hex', 'Binary']
#         self.inputAreas = []
#         self.inputFormats = []
#         for i in range(1, 6):
#             inputSizer = wx.BoxSizer(wx.HORIZONTAL)
#             self.inputAreas.append(
#                 wx.TextCtrl(self, wx.ID_ANY, '',
#                                         style=wx.TE_LEFT|wx.TE_PROCESS_ENTER,
#                                         size=(200,25)))
#             self.Bind(wx.EVT_TEXT_ENTER, self.OnSendInput, self.inputAreas[-1])
#             inputSizer.Add(wx.StaticText(self, wx.ID_ANY, " " + str(i)+" : "))
#             inputSizer.Add(self.inputAreas[-1], 4)
#             self.inputFormats.append(
#                 wx.Choice(self, id=wx.ID_ANY, choices=formatTypes))
#             inputSizer.Add(self.inputFormats[-1])
#             inputAreasSizer.Add(inputSizer)
        ### Input Type Radios
        #self.inputTypeRadios = wx.RadioBox(self, wx.ID_ANY,
        #                                                                     style=wx.RA_VERTICAL, label="TX Format",
        #                                                                     choices = ('Ascii', 'Decimal', 'Hex', 'Binary'),
        #                                                                     size=(100,25*len(self.inputAreas)))
        #lowerAreaSizer2.Add(self.inputTypeRadios)
        # Connect Quick Buttons
#         connectButtonSizer = wx.BoxSizer(wx.VERTICAL)
#         ## Connect/Disconnect Button
#         self.connectButton = wx.Button(self, id=wx.ID_ANY, label="    Disconnect    ")
#         self.connectButton.SetBackgroundColour(wx.Colour(255, 0, 0))
#         self.Bind(wx.EVT_BUTTON, self.OnToggleConnectButton, self.connectButton)
#         connectButtonSizer.Add(self.connectButton)
#         ## Auto Disconnect CheckBox
#         self.autoDisconnectCheck = wx.CheckBox(self, id=wx.ID_ANY,
#             label="Auto Disconnect")
#         connectButtonSizer.Add(self.autoDisconnectCheck)
#         ## Print Sent Data to Terminal CheckBox
#         self.printSentData = wx.CheckBox(self, id=wx.ID_ANY,
#             label="Print Sent Data to Terminal")
#         self.printSentData.SetValue(True) # checked by default
#         connectButtonSizer.Add(self.printSentData)                
#         lowerAreaSizer2.AddStretchSpacer()
#         lowerAreaSizer2.Add(connectButtonSizer)
#         mainSizer.Add(lowerAreaSizer, 0)
#         mainSizer.Add(outputSizer, pos = (1, 0), flag = wx.EXPAND)

        # Setup and get ready to roll
#         self.serialCon = serial.Serial()
#         self.SetStatusText('Not Connected...')

#         bordering = wx.GridBagSizer(0, 0)
#         bordering.Add(mainSizer, pos = (0, 0), flag = wx.ALL | wx.EXPAND, border = 5)
#         bordering.AddGrowableRow(0)
#         bordering.AddGrowableCol(0)
#         self.SetSizer(bordering)
        self.SetSizer(self.mainLayout)
        self.Show(True)
#         self.connected = False
        self.start()
#         self.connectButton.SetLabel("Connect")


    ##################################################
    def OnChangeDisplay(self, event):
        """Gets called when the user changes the display format"""
#         self.serialOutput.Clear()
#         self.historyLock.acquire()
#         self.appendToDisplay(self.history)
#         self.historyLock.release()

    ##################################################
    def readDefaults(self):
        menumap = {
#             'baud'         : self.baudMenu,
#             'parity'     : self.parityMenu,
#             'bytesize' : self.byteMenu,
#             'stopbits' : self.stopbitsMenu
        }
        for k, v in menumap.items():
            if self.cfg.Exists(k):
                default = self.cfg.Read(k)
                for item in v.GetMenuItems():
                    if item.GetLabel() == default:
                        item.Check(True)

#         for item in self.flowMenu.GetMenuItems():
#                 item.Check(self.cfg.ReadBool(item.GetLabel(), defaultVal=False))

        if self.cfg.Exists('portname'):
            self.portName = self.cfg.Read('portname')

    ##################################################
    def run(self):
        """The runtime thread to pull data from the open serial port"""
        while True:
            pass
#             if self.connected:
# 
#                 try:
#                     byte = self.serialCon.read()
#                 except:
#                     self.connected = False
#                     self.SetStatusText('Not Connected...')
#                     continue
# 
#                 if byte != '':
#                     historyEntry = {'type':'RX', 'data':byte}
#                     self.historyLock.acquire()
#                     self.history.append(historyEntry)
#                     self.historyLock.release()
#                     wx.CallAfter(self.appendToDisplay,[historyEntry])
#             else:
#                 time.sleep(.2)


    ##################################################
    def intToBinString(self,n):
        string = ''
        for i in range(0, 8):
            if (n&1): string = '1' + string
            else:         string = '0' + string
            n = n >> 1
        return string

    ##################################################
    def appendToDisplay(self, newEntries):
        if newEntries == None:
            return

        typeString = self.displayTypeRadios.GetStringSelection()

        entryCopies = []

        if typeString == 'Ascii':
            entryCopies = newEntries
        else:
            trans = None
            if(typeString     == 'Binary'):
                trans = self.intToBinString
            elif(typeString == 'Decimal'):
                trans = str
            elif(typeString == 'Hex'):
                trans = hex
            for entry in newEntries:
                entryCopies.append({'type':entry['type'], 'data':trans(ord(entry['data']))})

        for entry in entryCopies:
            # Set the proper output color
            if(entry['type'] == 'RX'):
                self.serialOutput.SetDefaultStyle(rxStyle)
            else:
                self.serialOutput.SetDefaultStyle(txStyle)

            # If the byte to show isn't valid ascii, then just print out ascii 1
            # as a placeholder
            try:
                self.serialOutput.AppendText(entry['data'])
            except:
                self.serialOutput.AppendText(chr(1))

            if typeString != 'Ascii':
                self.serialOutput.AppendText(' ')


    ##################################################
    def OnSetPort(self, event):
        self.portName = wx.GetTextFromUser('Port: ', 'Select Port Name', self.portName)

    ##################################################
    def OnSetConnection(self, event):
        if self.portName == "":
            self.OnSetPort(None)
            return

        baudRadio     = None
        for b in self.baudRadios:     
            if b.IsChecked(): baudRadio     = b
        parityRadio = None
        for p in self.parityRadios:
            if p.IsChecked(): parityRadio = p
        byteRadio     = None
        for b in self.byteRadios:
            if b.IsChecked(): byteRadio     = b
        stopRadio     = None
        for s in self.stopbitsRadios:
            if s.IsChecked(): stopRadio     = s

        self.serialCon = serial.Serial()
        self.serialCon.port         = self.portName
        self.serialCon.baudrate = int(baudRadio.GetLabel())
        self.serialCon.bytesize = bytesizeMap[byteRadio.GetLabel()]
        self.serialCon.parity     = parityMap[parityRadio.GetLabel()]
        self.serialCon.stopbits = stopMap[stopRadio.GetLabel()]
        self.serialCon.xonxoff    = self.xonoffCheck.IsChecked()
        self.serialCon.rtscts     = self.rtsctsCheck.IsChecked()
        self.serialCon.dsrdtr     = self.dsrdtrCheck.IsChecked()
        self.serialCon.timeout    = .3

        self.cfg.Write('portname', self.portName)
        self.cfg.Write('baud',         baudRadio.GetLabel())
        self.cfg.Write('parity',     parityRadio.GetLabel())
        self.cfg.Write('bytesize', byteRadio.GetLabel())
        self.cfg.Write('stopbits', stopRadio.GetLabel())
        for item in self.flowMenu.GetMenuItems():
            self.cfg.WriteBool(item.GetLabel(),item.IsChecked())

        try:
            self.serialCon.open()
        except serial.SerialException as ex:
            self.autoDisconnectCheck.SetValue(False)
            wx.MessageDialog(None, str(ex), 'Serial Error', wx.OK | wx.ICON_ERROR).ShowModal()
            self.SetStatusText('Not Connected...')
            self.connected = False
            return

        self.SetStatusText('Connected to ' + self.portName + ' ' + baudRadio.GetLabel() + 'bps')
        self.connected = True
        self.connectButton.SetBackgroundColour(wx.Colour(0, 255, 0))
        self.connectButton.SetLabel("Disconnect")

    ##################################################
    def OnClearOutput(self, event):
        self.historyLock.acquire()
        self.serialOutput.Clear()
        self.history = []
        self.historyLock.release()

    ##################################################
    def OnCloseConnection(self, event):
        self.connected = False

        self.serialCon.close()

        self.SetStatusText('Not Connected...')
        self.connectButton.SetBackgroundColour(wx.Colour(255, 0, 0))
        self.connectButton.SetLabel("Connect")

    ##################################################
    def OnSendLiveType(self, event):
        inputArea = event.GetEventObject()
        inputString = str(inputArea.GetString(0,-1))
        if inputString == "":
            return
        inputArea.Clear()
        if self.serialCon.isOpen():
            newHistoryVals = []
            for c in inputString:
                newHistoryVals.append({'type':'TX', 'data':c})

            self.historyLock.acquire()
            self.history = self.history + newHistoryVals
            self.historyLock.release()
            if self.printSentData.IsChecked():
                self.appendToDisplay(newHistoryVals)
            self.serialCon.write(inputString)

    ##################################################
    def OnSendInput(self, event):
        inputArea = event.GetEventObject()
        inputArea.SetSelection(0,-1)
        inputString = inputArea.GetString(0,-1)

        inputAreaIdx = -1
        for i in range(0, len(self.inputAreas)):
            if inputArea == self.inputAreas[i]:
                inputAreaIdx = i
                break
        if inputAreaIdx == -1:
            print "ERROR! Bad Input Area!"
            exit()

        inputVal = ''
        typeString = self.inputFormats[i].GetStringSelection()

        if(typeString == 'Ascii'):
            inputVal = str(inputString)
        else:
            base = 0
            if(typeString     == 'Binary'):
                base = 2
            elif(typeString == 'Decimal'):
                base = 10
            elif(typeString == 'Hex'):
                base = 16
            numStrings = inputString.split(" ")
            for numString in numStrings:
                numString = numString.strip()
                if numString == '': continue
                intVal = int(numString, base)
                inputVal += chr(intVal)
            
#         if self.serialCon.isOpen():
#             newHistoryVals = []
#             for c in inputVal:
#                 newHistoryVals.append({'type':'TX', 'data':c})
#             self.historyLock.acquire()
#             self.history = self.history + newHistoryVals
#             self.historyLock.release()
#             self.serialCon.write(inputVal)
#             if self.printSentData.IsChecked():
#                 self.appendToDisplay(newHistoryVals)

    ##################################################
    def OnAbout(self, event):
        dlg = wx.MessageDialog(self, "A set of useful serial utilities by "
                                   #             if self.connected:
# 
#                 try:
#                     byte = self.serialCon.read()
#                 except:
#                     self.connected = False
#                     self.SetStatusText('Not Connected...')
#                     continue
# 
#                 if byte != '':
#                     historyEntry = {'type':'RX', 'data':byte}
#                     self.historyLock.acquire()
#                     self.history.append(historyEntry)
#                     self.historyLock.release()
#                     wx.CallAfter(self.appendToDisplay,[historyEntry])
#             else:
#                 time.sleep(.2)                              "Randolph Voorhies (rand.voorhies@gmail.com)\n"
                                                                 "http://ilab.usc.edu/~rand",
                                                                 "About randterm", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    ##################################################
    def OnExit(self, e):
        self.Close(True)

    ##################################################
    def OnToggleConnectButton(self, event):
        if(self.connected):
            self.OnCloseConnection(None)
        else:
            self.OnSetConnection(None)

    def OnActivate(self, event):
        pass
#         if self.autoDisconnectCheck.IsChecked():
#             if event.GetActive():
#                 self.OnSetConnection(None)
#             else:
#                 self.OnCloseConnection(None)


app = wx.App(False)
frame = randtermFrame(None, "randterm")
app.MainLoop()
