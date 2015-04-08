#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os
import numpy as np
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import cv2

try:
    from PyQt4 import QtGui, QtCore, Qt
except Exception, detail:
    print 'No PyQt-Module installed.'
    quit()

# #######################################

# print QtCore.QString(os.)
# quit()


class Main(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self)

        # #######################################

        # GEOMETRY
        width = 900
        hight = 900
        offsetLeft = 0
        offsetTop = 0

        self.setGeometry(offsetLeft, offsetTop, width, hight)
        # self.setFixedSize(width,hight)
        self.setWindowTitle('Manual Chirp-Detector')
        self.mainLayout = QtGui.QVBoxLayout()
        self.setLayout( self.mainLayout )

        # #######################################
        
        self.legs = ['left front', 'left center', 'left back',
                     'right back', 'right center', 'right front']
        self.nframe = 0
        self.vf = None
        self.nleg = 0
        self.image = None
        self.annotations = list()
        self.anno_xy = list()

        # #######################################

        # THE PLOT
        self.figure = plt.figure()
        params = {'axes.labelsize': 22,
                  'font.size': 16,
                  'ytick.labelsize': 16,
                  'xtick.labelsize': 16}
        plt.rcParams.update(params)
        self.canvas = Canvas(self.figure, parent=self)
        self.toolbar = NavigationToolbar( self.canvas, parent=self)
        self.mainLayout.addWidget(self.canvas)
        self.mainLayout.addWidget(self.toolbar)
        plt.subplots_adjust(left=0., right=1., bottom=0., top=1.)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_axis_off()

        # The click-tool
        self.figure.canvas.mpl_connect('button_press_event', self.onclick)

        # #######################################

        # BUTTON
        self.load_video_button = QtGui.QPushButton('Load video file', parent=self)
        self.load_video_button.setMinimumHeight( 100 )
        self.load_video_button.setMinimumWidth( 200 )

        self.previous_frame_button = QtGui.QPushButton('Previous frame', parent=self)
        self.previous_frame_button.setMinimumHeight( 100 )
        self.previous_frame_button.setMinimumWidth( 200 )

        self.next_frame_button = QtGui.QPushButton('Next frame', parent=self)
        self.next_frame_button.setMinimumHeight( 100 )
        self.next_frame_button.setMinimumWidth( 200 )

        self.done_button = QtGui.QPushButton('Done!', parent=self)
        self.done_button.setMinimumHeight( 100 )
        self.done_button.setMinimumWidth( 200 )

        s = ''
        self.label = QtGui.QLabel(s , parent=self)
        self.label.setStyleSheet('font-size: 28pt')

        hbox_label = QtGui.QHBoxLayout()
        hbox_label.addStretch(1)
        hbox_label.addWidget(self.label)
        hbox_label.addStretch(1)
        self.mainLayout.addLayout(hbox_label)

        hbox_button = QtGui.QHBoxLayout()
        hbox_button.addStretch(1)
        hbox_button.addWidget(self.load_video_button)
        hbox_button.addWidget(self.previous_frame_button)
        hbox_button.addWidget(self.next_frame_button)
        hbox_button.addStretch(1)
        hbox_button.addWidget(self.done_button)
        self.mainLayout.addLayout(hbox_button)

        # #######################################

        # CONNECTIONS
        self.connect(self.load_video_button, QtCore.SIGNAL('clicked()'), self.load_video)
        self.connect(self.previous_frame_button, QtCore.SIGNAL('clicked()'), self.previous_frame)
        self.connect(self.next_frame_button, QtCore.SIGNAL('clicked()'), self.next_frame)
        self.connect(self.done_button, QtCore.SIGNAL('clicked()'), self.done)
        self.create_actions()

        # #######################################

        # initialize plot ...
        # self.load_video(vf)

    def onclick(self, event):
        if self.toolbar._active is not None:
            return

        if event.xdata is None or event.ydata is None:
            # print('failure: invalid value! try again!')
            return

        if self.vf is None:
            return

        # info
        # print 'button=%d, x=%d, y=%d, xdata=%f, ydata=%f'%(
        #     event.button, event.x, event.y, event.xdata, event.ydata)
        
        # get coordinates; in pixels
        x = int(np.round(event.xdata))
        y = int(np.round(event.ydata))

        # save coordinates
        self.data[self.nframe, 2+self.nleg*2] = x
        self.data[self.nframe, 2+self.nleg*2+1] = y
        print('{2} -- x: {0}; y: {1}'.format(x,y, self.legs[self.nleg]))
        
        # increment leg count
        if self.nleg < len(self.legs)-1:
            self.nleg += 1
        else:
            self.nleg = 0
        self.label.setText('frame {0}: '.format(self.nframe) + self.legs[self.nleg])

        self.annotate()
        self.figure.canvas.draw()

    def load_video(self):
        if self.vf is not None and self.vf.isOpened():
            s = 'File is already open. Close it before you continue.'
            self.label.setText(s)
            return

        vf = str(QtGui.QFileDialog.getOpenFileName(self,
                'Open video file', QtCore.QDir.currentPath(), 
                'AVI (*.avi)').toUtf8())

        if not os.path.exists(vf):
            return
        self.vf = cv2.VideoCapture(vf)
        if not self.vf.isOpened(): 
            s = 'Error: could not open file!'
            self.label.setText(s)
            return

        self.setWindowTitle(os.path.basename(vf))
        self.label.setText('frame {0}: '.format(self.nframe) + self.legs[self.nleg])

        # get framecount
        self.length = int(self.vf.get(7))
        self.fps = self.vf.get(5)
        self.w = int(self.vf.get(3))
        self.h = int(self.vf.get(4))

        # create container
        ## frame, time, ... 
        ## left1x, left1y, left2x, left2y, left3x, left3y,...
        ## right1x, right1y, right2x, right2y, right3x, right3y
        self.data = np.zeros((self.length, 14))

        # look for existing file; 
        ## if not available: create new container and outputfile
        base = os.path.splitext(os.path.basename(vf))[0]
        self.data_fn = base + '_tracking.dat'

        try:
            if os.path.exists(self.data_fn):
                olddata = np.genfromtxt(self.data_fn)
                if olddata.shape == self.data.shape:
                    self.data = olddata
                    print('Previous data loaded!')
        except Exception:
            pass

        # check for existing data files
        # if os.path.exists(fn):
        #     # a message box
        #     chirp_str = ' '.join(str(s) for s in self.bad_chirps)
        #     msgbox = QtGui.QMessageBox(parent=self)
        #     msgbox.setText("The chirplist has been modified.")
        #     msgbox.setInformativeText("Do you want to save your changes?")
        #     msgbox.setDetailedText(chirp_str)
        #     msgbox.setStandardButtons(msgbox.Save | msgbox.Cancel)
        #     msgbox.setDefaultButton(msgbox.Save)
        #     answer = msgbox.exec_()
        #     if answer == msgbox.Save:
            #     k = 0
            #     while True:
            #         if os.path.exists()
                # elif answer == msgbox.Cancel:
                #     print 'Changes not saved.'

        self.ax.set_ylim(self.h, 0)
        self.ax.set_xlim(0, self.w)
        self.display_frame()

    def clear_frame(self):
        self.data[self.nframe, :] = 0.
        self.annotate()
        self.figure.canvas.draw()

    def close_video(self):
        if self.vf is not None:
            self.vf.release()
            self.length = 0
            self.fps = 0
            self.w = 0
            self.h = 0
            self.vf = None
        self.setWindowTitle(os.path.basename(''))
        if self.image is not None:
            self.image.remove()
            self.image = None
            self.remove_annotations()
            self.figure.canvas.draw()

    def display_frame(self):
        # remove previous frame
        if self.image is not None:
            self.image.remove()
            self.image = None

        # get current frame
        self.vf.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, self.nframe)
        _, frame = self.vf.read()
        self.image = self.ax.imshow(frame, cmap=cm.Greys_r)
        self.label.setText('frame {0}: '.format(self.nframe) + self.legs[self.nleg])
        
        # update data
        self.data[self.nframe, 0] = self.nframe
        self.data[self.nframe, 1] = 1.*self.nframe/self.fps
        self.annotate()
        self.figure.canvas.draw()

    def annotate(self):
        color='red'
        # remove previous entry
        self.remove_annotations()
        for d in xrange(6):
            x = self.data[self.nframe, 2+d*2]
            y = self.data[self.nframe, 2+d*2+1]
            s = '{0}'.format(d+1)
            if x != 0 and y != 0:
                # print 'annotate!', x, y
                an = self.ax.annotate(s, xy=(x, y), xycoords='data', fontsize=18,
                        xytext=(0, 0), textcoords='offset points', color=color)
                self.annotations.append(an)
                anxy, = self.ax.plot(x, y, 'x', ms=15, mec=color, 
                            mfc=color, zorder=1000, mew=2)
                self.anno_xy.append(anxy)

    def remove_annotations(self):
        for an in self.annotations:
            an.remove()  # remove from figure
        self.annotations = list()

        for an in self.anno_xy:
            an.remove()  # remove from figure
        self.anno_xy = list()

    def previous_frame(self):
        if self.vf is None:
            return
        if self.nframe != 0:
            self.nframe -= 1
        else:
            self.nframe = self.length-1
        self.save_data()
        self.remove_annotations()
        self.display_frame()

    def next_frame(self):
        if self.vf is None:
            return
        if self.nframe != self.length-1:
            self.nframe += 1
        else:
            self.nframe = 0

        # if data for next frame is untouched, use previous dataset as default
        if 0 < self.nframe < self.length-1 and \
            np.all(self.data[self.nframe, 2:] == 0.):
            self.data[self.nframe, 2:] = self.data[self.nframe-1, 2:]
        self.save_data()
        self.remove_annotations()
        self.display_frame()

    def save_data(self):
        if self.vf is None:
            return
        with open(self.data_fn, 'w') as f:
            header = '# frame index, time [s], '
            header += 'left_front_x, left_front_y, left_center_x, left_center_y, left_back_x, left_back_y, '
            header += 'right_front_x, right_front_y, right_center_x, right_center_y, right_back_x, right_back_y\n'
            f.write(header)

            for i in xrange(self.data.shape[0]):
                d = self.data[i, :]
                # frame and time
                f.write('{0} {1:.3f} '.format(int(d[0]), d[1]))
                pos = ' '.join([str(int(num)) for num in d[2:]])
                f.write(pos + '\n')

    def done(self):
        print('Closing file and saving.')
        self.save_data()
        self.data = None
        self.close_video()

    def leg1(self):
        if self.vf is None:
            return
        self.nleg=0
        self.label.setText('frame {0}: '.format(self.nframe) + self.legs[self.nleg])

    def leg2(self):
        if self.vf is None:
            return
        self.nleg=1
        self.label.setText('frame {0}: '.format(self.nframe) + self.legs[self.nleg])

    def leg3(self):
        if self.vf is None:
            return
        self.nleg=2
        self.label.setText('frame {0}: '.format(self.nframe) + self.legs[self.nleg])

    def leg4(self):
        if self.vf is None:
            return
        self.nleg=3
        self.label.setText('frame {0}: '.format(self.nframe) + self.legs[self.nleg])

    def leg5(self):
        if self.vf is None:
            return
        self.nleg=4
        self.label.setText('frame {0}: '.format(self.nframe) + self.legs[self.nleg])

    def leg6(self):
        if self.vf is None:
            return
        self.nleg=5
        self.label.setText('frame {0}: '.format(self.nframe) + self.legs[self.nleg])

    def create_actions(self):

        self.actionLoad = QtGui.QAction("Load video file", self)
        self.actionLoad.setShortcut(Qt.Qt.Key_L)
        self.connect(self.actionLoad, QtCore.SIGNAL('triggered()'), self.load_video)
        self.addAction(self.actionLoad)

        self.actionPF = QtGui.QAction("Previous frame", self)
        self.actionPF.setShortcut(Qt.Qt.Key_A)
        self.connect(self.actionPF, QtCore.SIGNAL('triggered()'), self.previous_frame)
        self.addAction(self.actionPF)

        self.actionNF = QtGui.QAction("Next frame", self)
        self.actionNF.setShortcut(Qt.Qt.Key_D)
        self.connect(self.actionNF, QtCore.SIGNAL('triggered()'), self.next_frame)
        self.addAction(self.actionNF)

        self.actionCF = QtGui.QAction("Clear frame", self)
        self.actionCF.setShortcut(Qt.Qt.Key_C)
        self.connect(self.actionCF, QtCore.SIGNAL('triggered()'), self.clear_frame)
        self.addAction(self.actionCF)

        # Select leg
        self.actionL1 = QtGui.QAction("Next Window", self)
        self.actionL1.setShortcut(Qt.Qt.Key_1)
        self.connect(self.actionL1, QtCore.SIGNAL('triggered()'), self.leg1)
        self.addAction(self.actionL1)

        self.actionL2 = QtGui.QAction("Next Window", self)
        self.actionL2.setShortcut(Qt.Qt.Key_2)
        self.connect(self.actionL2, QtCore.SIGNAL('triggered()'), self.leg2)
        self.addAction(self.actionL2)

        self.actionL3 = QtGui.QAction("Next Window", self)
        self.actionL3.setShortcut(Qt.Qt.Key_3)
        self.connect(self.actionL3, QtCore.SIGNAL('triggered()'), self.leg3)
        self.addAction(self.actionL3)

        self.actionL4 = QtGui.QAction("Next Window", self)
        self.actionL4.setShortcut(Qt.Qt.Key_4)
        self.connect(self.actionL4, QtCore.SIGNAL('triggered()'), self.leg4)
        self.addAction(self.actionL4)

        self.actionL5 = QtGui.QAction("Next Window", self)
        self.actionL5.setShortcut(Qt.Qt.Key_5)
        self.connect(self.actionL5, QtCore.SIGNAL('triggered()'), self.leg5)
        self.addAction(self.actionL5)

        self.actionL6 = QtGui.QAction("Next Window", self)
        self.actionL6.setShortcut(Qt.Qt.Key_6)
        self.connect(self.actionL6, QtCore.SIGNAL('triggered()'), self.leg6)
        self.addAction(self.actionL6)

    def closeEvent(self, event):
        self.done()
        self.emit(QtCore.SIGNAL("closed"))

# #######################################

class Canvas( FigureCanvas ):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__( self, fig, parent=None ):

        FigureCanvas.__init__(self, fig)
        FigureCanvas.setSizePolicy(self,
            QtGui.QSizePolicy.Expanding,
            QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


# #######################################

if __name__=="__main__":

    args = sys.argv
    qapp = QtGui.QApplication(sys.argv)
    main = Main()
    main.show()
    qapp.exec_()
