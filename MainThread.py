from CameraControl import *
from RobotControl import *
import cv2
import time
import glob
import csv
import numpy as np
from PyQt5.QtCore import pyqtSignal, QThread
import math

class Main_loop(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    send_fps = pyqtSignal(str)
    send_msg = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.r = RobotControl()
        self.camera = CameraControl() 
        self.picking = False
        self.destXYZ_obj = [[100, 100, -50], [200, 200, -50], [200, 100, -60]]
        self.cam_flag = False
        self.auto_run = False
        self.XYZ_obj = []
        self.v_robot = 200
        ## Reset conveyor
        self.r.writeByte(2, 0)

    def run(self):
        ## Reset byte to 0
        self.r.writeByte(1, 0)
        self.r.writeByte(5, 0)
        
        ## Start main job
        self.r.mainJobStart()

        self.auto_run = True

        self.r.servoON()

        while(self.cam_flag and self.auto_run):
            if (self.picking and len(self.XYZ_obj) > 0):
                try:
                    # Get object position and destination position
                    x, y, z = self.XYZ_obj[0]['center_x'], self.XYZ_obj[0]['center_y'], self.XYZ_obj[0]['height']
                    velocity = 35
                    t1 = 2.11
                    y = str(float(y) + velocity * t1)
                    # x, y, z = self.estimatePos(xc, yc, zc, x, y, z)
                    dest_x, dest_y, dest_z = "-11.53", "-258.413", "-34.826"
                    self.XYZ_obj.pop(0)
                    print(x, y, z)
                    
                    self.r.writePos(30, x, y, z)
                    self.r.writePos(36, dest_x, dest_y, dest_z)
                    self.r.writeByte(5, 1)
                    while(self.r.ReadByte(5)[32]==1):
                        pass

                    self.r.writeByte(6, 1)

                    while(self.r.ReadByte(2)[32]==1):
                        pass

                    self.r.writeByte(6, 0)

                    self.picking = False
                    self.send_msg.emit("Picking & Placing...")
                except:
                    pass


    def camera_run(self):
        self.cam_flag = True
        profile = self.camera.pipeline.start(self.camera.config)
        # stream_profile_depth = profile.get_stream(rs.stream.depth)
        stream_profile_color = profile.get_stream(rs.stream.color)
        self.camera.cam_intrinsic = stream_profile_color.as_video_stream_profile().get_intrinsics()
        
        while self.cam_flag:
            # Changed model
            if (self.camera.cur_weights != self.camera.weights):
                self.camera.cur_weights = self.camera.weights
                self.camera.model = torch.hub.load('E:/yolov5', 'custom', path=self.camera.cur_weights, source='local')

            frames = self.camera.pipeline.wait_for_frames()
            # frames = self.camera.align.process(frames)
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()
            if not depth_frame or not color_frame:
                continue

            # Convert images to numpy arrays
            # depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())
            self.camera.result, self.XYZ_obj = self.camera.process(color_image, depth_frame)
            
            if (not self.picking) and (len(self.XYZ_obj)>0):
                self.r.writeByte(2, 1)
                self.picking = True
            
            self.change_pixmap_signal.emit(self.camera.result)
            self.send_fps.emit(self.camera.fps)      
            
    def read_conveyor(self):
        v = 45.2
        return v

    def estimatePos(self, x, y, z, x0, y0, z0):
        # x, y, z, x0, y0, z0 = float(x), float(y), float(z), float(x0), float(y0), float(z0)
        # v_conveyor = self.read_conveyor()
        # v_robot = self.v_robot
        # a = (v_robot**2 / v_conveyor**2) - 1
        # b = 2*(y - y0 * (v_robot**2 / v_conveyor**2))
        # c = y0**2 * v_robot**2 / v_conveyor **2 - (x-x0)**2 - (z-z0)**2 - y**2
        # delta = math.sqrt(b**2 - 4*a*c)
        # y_new = (-b + delta)/+2/a
        y_new = str(float(y0) + 25)
        return x0, y_new, z0
