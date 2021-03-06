import argparse
import cv2
import glob
import json
import os
import re
import time

import numpy as np

from matplotlib import pyplot as plt
from pathlib import Path
from scipy.stats import norm

PINGPONG_DIAMETER_CM = 4

# Next: 1) Show arrow of velocity estimate in plot + past trajectory
class motionTracker:

    def __init__(self, image_path, n_particles=20, sigma_init_pos=40,
                 sigma_init_vel=1, process_noise_pos_sigma=25,
                 process_noise_vel_sigma=20, measurement_noise=20, n_steps=100,
                 n_states=4, n_bins=50, show_extended=False, particle_filter=True,
                 frames_to_process=1):
        self.image_path = image_path
        self.image = self.load_image(self.image_path)
        self.ball_center = np.zeros((frames_to_process,1,2))
        self.ball_radius = np.zeros((frames_to_process,1,1))
        self.ball_center_vel = np.zeros(( frames_to_process,1,2))
        self.frame_count = -1

        if particle_filter:
            self.n_particles = n_particles
            self.sigma_init_pos = sigma_init_pos
            self.sigma_init_vel = sigma_init_vel
            self.process_noise_pos_sigma = process_noise_pos_sigma
            self.process_noise_vel_sigma = process_noise_vel_sigma
            self.measurement_noise_sigma = measurement_noise
            self.n_steps = n_steps
            self.n_states = n_states
            self.n_bins = n_bins
            self.show_extended = show_extended
            self.compute_init_variance()
            self.compute_process_noise_variance()
            self.target_ROI = self.get_ROI(self.image)
            self.get_target_hist()
            self.init_particles()

    def compute_circle_hist(self, circle, img):
        height,width = img.shape
        mask_circle = np.zeros((height,width), np.uint8)
        cv2.circle(mask_circle,(circle[0],circle[1]),circle[2], 1,thickness=-1)
        masked_data = cv2.bitwise_and(img, img, mask=mask_circle)
        mask_circle_boolean = mask_circle <= 0
        masked_array = np.ma.array(masked_data, mask=mask_circle_boolean)
        data_ball = masked_array[~mask_circle_boolean].data
        ball_hist = np.histogram(data_ball, bins=20, range=(0, 256))
        return (masked_data, ball_hist, data_ball)

    def track_ball_hough(self, show=False, save=False, store_name='image.png',
                         target_radius=26, dt=1/25, frames_to_process=-1):
        self.frame_count += 1
        img = cv2.medianBlur(self.convert_to_grayscale(self.image), 5)
        cimg = self.image
        radius_variation = 5
        circles = cv2.HoughCircles(img ,cv2.HOUGH_GRADIENT,1,20,param1=50,param2=30,
                                   minRadius=target_radius - radius_variation,
                                   maxRadius=target_radius + radius_variation)
        circle_hists = dict()
        # Update the position of the ball center
        min_distance = -1
        if not circles is None:
            new_pos = np.zeros((1,2))
            if self.frame_count > 0:
                new_pos[0,0] = self.ball_center[self.frame_count - 1,0,0]
                new_pos[0,1] = self.ball_center[self.frame_count - 1,0,1]
            for i in range(len(circles[0,:])):
                circle = circles[0,i]
                if min_distance < 0 or np.abs(circle[2] - target_radius) < min_distance:
                    new_pos[0,0] = circle[0]
                    new_pos[0,1] = circle[1]
                    self.ball_radius[self.frame_count,0,0] =  circle[2]
            if self.frame_count > 0:
                cm_per_pixel = None
                if self.ball_radius[self.frame_count,0,0] > 0:
                    cm_per_pixel = PINGPONG_DIAMETER_CM / (2 * self.ball_radius[self.frame_count,0,0])
                self.ball_center_vel[self.frame_count,0,0] = (new_pos[0,0] - 
                                                          self.ball_center[self.frame_count - 1, 0,0]) / dt * cm_per_pixel
                self.ball_center_vel[self.frame_count,0,1] = (new_pos[0,1] - 
                                                          self.ball_center[self.frame_count - 1,0,1]) / dt * cm_per_pixel
            
            self.ball_center[self.frame_count,0,0] = new_pos[0,0]
            self.ball_center[self.frame_count,0,1] = new_pos[0,1]
        if not circles is None:
            for i in range(len(circles[0,:])):
                circle = circles[0,i]
                circle_hists[i] = {'masked_data': None, 'ball_hist': None, 'data_ball': None,
                                    'radius': circle[2]}
                (circle_hists[i]['masked_data'], circle_hists[i]['ball_hist'],
                circle_hists[i]['data_ball']) = self.compute_circle_hist(circle, self.convert_to_grayscale(cimg))
                # draw the outer circle
                cv2.circle(cimg,(circle[0],circle[1]),circle[2],(0,255,0),2)
                # draw the center of the circle
                cv2.circle(cimg,(circle[0],circle[1]),2,(0,0,255),3)
        
        if show or save:
            fig = plt.figure(figsize=(20, 12))
            ax1 = fig.add_subplot(len(circle_hists) + 1, 2, 1)
            plt.title('Detected circles')
            plt.imshow(cimg[..., ::-1])
            ax2 = fig.add_subplot(len(circle_hists) + 1, 2, 2)
            plt.plot(np.linalg.norm(self.ball_center_vel[:self.frame_count+1,0,:], axis=1),
                    linestyle='--', marker='o', color='b')
            ax2.set_ylabel('[cm/s]')
            ax2.set_xlabel('frame')
            ax2.grid(True)
            ax2.set_ylim(0,20)
            if frames_to_process > 0:
                ax2.set_xlim(0,frames_to_process)
            plt.title('Ball speed [cm/s]')
            if not circles is None:
                for i in range(len(circles[0,:])):
                        fig.add_subplot(len(circle_hists) + 1, 2, 3 + i * 2)
                        plt.imshow(circle_hists[i]['masked_data'], cmap='gray', vmin=0, vmax=255)
                        plt.title('Extracted ball: {0} with radius: {1}'.format(str(i),
                        str(round(circle_hists[i]['radius'],1))))
                        fig.add_subplot(len(circle_hists) + 1, 2, 4 + i * 2)
                        plt.hist(circle_hists[i]['data_ball'], bins=50, range=(0,255))
                        plt.title('Hist of ball: {}'.format(str(i)))
            
        if save:
                plt.savefig(store_name, bbox_inches='tight')
        if show:
            plt.draw()
            plt.waitforbuttonpress(0)
        if save or show:
            plt.close()

    def get_new_image(self, image_path):
        self.image_path = image_path
        self.image = self.load_image(self.image_path)

    def compute_process_noise_variance(self):
        self.V_process_noise = np.diag([self.process_noise_pos_sigma,
                                        self.process_noise_pos_sigma,
                                        self.process_noise_vel_sigma,
                                        self.process_noise_vel_sigma])

    def compute_init_variance(self):
        self.P0_init = np.diag([self.sigma_init_pos, self.sigma_init_pos,
                                self.sigma_init_vel, self.sigma_init_vel])

    def get_ROI(self, img):
        # Select ROI
        fromCenter = False
        r = cv2.selectROI(img, fromCenter)

        # Crop image
        width = int(r[1] + r[3]) - int(r[1])
        height = int(r[0] + r[2]) - int(r[0])
        im_crop = img[int(r[1]):int(r[1] + r[3]), int(r[0]):int(r[0] + r[2])]
        target_ROI = {'image': im_crop, 'image_gray':
                      self.convert_to_grayscale(im_crop),
                      'height': height, 'width': width,
                      'target_midpoint_x': int(r[0]) + height / 2,
                      'target_midpoint_y': int(r[1]) + width / 2}
        cv2.destroyAllWindows()
        return target_ROI

    def load_image(self, image_path):
        im = cv2.imread(image_path)
        return im

    def get_target_hist(self):
        plt.subplot(121), plt.imshow(self.target_ROI['image_gray'], 'gray')
        plt.subplot(122)
        self.target_hist = dict()
        self.target_hist['values'], self.target_hist['bins'], _ = plt.hist(
            self.target_ROI['image_gray'].ravel(), self.n_bins, [0, 256])
        plt.show()

    @staticmethod
    def convert_to_grayscale(img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return gray

    def init_particles(self):
        self.X_p = np.zeros((self.n_steps, self.n_states, self.n_particles))
        mean_init = np.array([[self.target_ROI['target_midpoint_x']],
                              [self.target_ROI['target_midpoint_y']],
                              [0],
                              [0]])
        self.X_p[0, :, :] = mean_init + \
            np.dot(self.P0_init, np.random.normal(
                size=(self.n_states, self.n_particles)))
        self.current_state = self.X_p[0, :, :]
        self.particle_boxes = np.zeros((4, self.n_particles))
        self.particle_histograms = np.zeros(
            (self.target_hist['values'].shape[0], self.n_particles))
        self.particle_betas = np.ones(
            (1, self.n_particles)) * 1 / self.n_particles
        self.compute_MMSE_estimate()

    def propagate_particles(self, dt):
        A = np.identity(self.n_states)
        A[0, 2] = dt
        A[1, 3] = dt
        self.current_state = np.dot(A, self.current_state) + \
            np.dot(self.V_process_noise, np.random.normal(
                size=(self.n_states, self.n_particles)))

    def update_particles(self):
        self.update_particles_histograms()
        self.compute_particle_betas()
        self.resample_particles()
        self.compute_MMSE_estimate()

    def compute_particle_betas(self):
        d_hellinger = self.compute_hellinger_distance(self.particle_histograms,
                                                      self.target_hist['values'])
        # Compute probability density values
        normal_density_values = norm.pdf(
            d_hellinger, 0, 1 / self.measurement_noise_sigma)
        self.particle_betas = normal_density_values / normal_density_values.sum()

    def compute_hellinger_distance(self, h_measured, h_target):
        # Normalize histograms
        h_measured_n = h_measured / h_measured.sum(axis=0)
        h_target_n = h_target / h_target.sum(axis=0)

        h_measured_n = h_measured_n.reshape(-1, 1) if len(
            h_measured_n.shape) < 2 else h_measured_n
        h_target_n = h_target_n.reshape(-1,
                                        1) if len(h_target_n.shape) < 2 else h_target_n
        d_hellinger = np.sqrt(1 - np.sqrt(h_measured_n *
                                          h_target_n).sum(axis=0))
        return d_hellinger

    def resample_particles(self):
        current_state_prior = self.current_state.copy()
        beta_cumsum = np.cumsum(self.particle_betas)
        index_selected = []
        for i in range(self.n_particles):
            randuni = np.random.uniform()
            res = np.asarray(randuni <= beta_cumsum).nonzero()
            index = res[0][0] if res[0].size > 0 else 0
            index_selected.append(index)
            self.current_state[:, i] = current_state_prior[:, index]

    def update_particles_histograms(self):
        image_grayscale = self.convert_to_grayscale(self.image)
        for i in range(self.n_particles):
            self.particle_boxes[:, i] = np.array([self.current_state[0, i] -
                                                  self.target_ROI['height'] / 2,
                                                  self.current_state[1, i] -
                                                  self.target_ROI['width'] / 2,
                                                  self.current_state[0, i] +
                                                  self.target_ROI['height'] / 2,
                                                  self.current_state[1, i] +
                                                  self.target_ROI['width'] / 2]).transpose()
            im_crop = image_grayscale[int(self.particle_boxes[1, i]):
                                      int(self.particle_boxes[3, i]),
                                      int(self.particle_boxes[0, i]):
                                      int(self.particle_boxes[2, i])]
            self.particle_histograms[:, i], _ = np.histogram(im_crop.ravel(),
                                                             bins=self.n_bins,
                                                             range=(0, 256))

            if self.show_extended:
                d_hellinger = self.compute_hellinger_distance(self.particle_histograms[:, i],
                                                              self.target_hist['values'])
                plt.subplot(2, 2, 1)
                plt.imshow(self.target_ROI['image_gray'], 'gray')
                plt.title('target')
                plt.subplot(2, 2, 2)
                plt.imshow(im_crop, 'gray')
                plt.title(str(i + 1) + '. particle')
                plt.subplot(2, 2, 3)
                plt.hist(self.target_hist['bins'][:-1], weights=self.target_hist['values'],
                         bins=self.target_hist['bins'], label='target')
                plt.legend()
                plt.subplot(2, 2, 4)
                plt.hist(self.target_hist['bins'][:-1], weights=self.particle_histograms[:, i],
                         bins=self.target_hist['bins'], label=str(i + 1) + '. particle, d_hel={0:0.2f}'.format(d_hellinger[0]))
                plt.legend()
                plt.show()
                plt.cla()

    def compute_MMSE_estimate(self):
        self.mmse_estimate = self.current_state.mean(axis=1).reshape(-1, 1)
        self.mmse_estimate_box = np.array([self.mmse_estimate[0, 0] -
                                           self.target_ROI['height'] / 2,
                                           self.mmse_estimate[1, 0] -
                                           self.target_ROI['width'] / 2,
                                           self.mmse_estimate[0, 0] +
                                           self.target_ROI['height'] / 2,
                                           self.mmse_estimate[1, 0] +
                                           self.target_ROI['width'] / 2]).transpose()

    def generate_processed_frame(self, particles, show=False, save=False, store_name='image.png'):
        # Radius of circle
        radius = 10
        # Red color in BGR
        color = (0, 0, 255)
        center_list = [(int(particles[0, i]), int(particles[1, i]))
                       for i in range(self.n_particles)]
        start_point_list = [(int(self.particle_boxes[0, i]),
                             int(self.particle_boxes[1, i]))
                            for i in range(self.particle_boxes.shape[1])]
        end_point_list = [(int(self.particle_boxes[2, i]),
                           int(self.particle_boxes[3, i]))
                          for i in range(self.particle_boxes.shape[1])]

        image_cp = self.image.copy()
        thickness_particles = 1
        thickness_mmse = 2
        color_blue = (255, 0, 0)
        color_green = (0, 255, 0)
        for center_point, start_point, end_point in zip(center_list, start_point_list, end_point_list):
            cv2.circle(image_cp, center_point,
                       radius=radius, color=color)
            cv2.rectangle(image_cp, start_point, end_point, color=color_blue,
                          thickness=thickness_particles)
        cv2.rectangle(image_cp, (int(self.mmse_estimate_box[0]),
                                 int(self.mmse_estimate_box[1])),
                      (int(self.mmse_estimate_box[2]),
                       int(self.mmse_estimate_box[3])),
                      color=color_green,
                      thickness=thickness_mmse)

        window_name = 'particles'

        # Displaying the image
        if show:
            while True:
                cv2.imshow(window_name, image_cp)
                if cv2.waitKey(1) & 0xFF == ord('n'):
                    break
        if save:
            cv2.imwrite(store_name, image_cp) 
        cv2.destroyAllWindows()


class imageSamples:

    def __init__(self, path_to_images, image_formater='.png', frame_period=None):
        self.path_to_images = path_to_images
        self.framelist = sorted(glob.glob(self.path_to_images + '/*' + image_formater), key=self.extract_number)
        if not frame_period:
            self.read_timestamps()
        else:
            self.dt = np.full(len(self.framelist), frame_period, dtype=float)
        self.image_dt_list = list(zip(self.framelist, self.dt))

    def read_timestamps(self, filename='timestamps.json'):
        json_file_path = Path(self.path_to_images + '/' + filename)
        with json_file_path.open() as json_file:
            data = json.load(json_file)
            self.timestamps = [float(time_stamp['pkt_pts_time'])
                               for time_stamp in data['frames']]
            self.dt = np.diff(self.timestamps)
            self.dt = np.insert(self.dt, 0, 0.0)
    
    def extract_number(self, name):
        match_obj = re.search('([0-9]+)\.png', name)
        number = -1
        if match_obj:
            number = int(match_obj.group(1))
        return number


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('frames_folder',
                        help='Folder where images are stored.')
    parser.add_argument('--n_particle', default=20, type=int,
                        help='Option to define number of particles.')
    parser.add_argument('--show_particles', '-sh', action='store_true',
                        help='Option to show each frame with particles. \
                              Press key n to continue to next frame')
    parser.add_argument('--save_frames', '-s', action='store_true',
                        help='Option to store processed frames.')
    parser.add_argument('--start_image', default=1, type=int,
                       help='First image to be processed. \
                       Input is integer with 1 representing the first image \
                       in the folder sorted by image name.')
    parser.add_argument('--end_image', default=-1, type=int,
                       help='Last image to be processed. \
                       Input is integer with 1 representing the first image \
                       in the folder sorted by image name.')
    parser.add_argument('--method', default='particle', type=str, help='Method of how tracker should work.\
                       Options are: particle, hough')
    parser.add_argument('--frame_period', default=None, type=float, help='Delta time period between frames')
    parser.add_argument('--target_radius', default=26, type=int, help='Radius of target ball size in pixels')
    args = parser.parse_args()
    image_folder = args.frames_folder
    images = imageSamples(path_to_images=image_folder, frame_period=args.frame_period)
    start_image = args.start_image
    save_path = image_folder + '/processed/'
    particle_filter = True if args.method == 'particle' else False
    if args.save_frames and not os.path.isdir(save_path):
        os.mkdir(save_path)
    if args.end_image < 0:
        considered_list = images.image_dt_list[start_image + 1:]
    else:
        considered_list = images.image_dt_list[start_image + 1:args.end_image + 1]
    
    frames_to_process = len(considered_list)
    
    ping_pong_tracker = motionTracker(
        image_path=images.image_dt_list[start_image][0],
        n_particles=args.n_particle, particle_filter=particle_filter,
        frames_to_process=frames_to_process)
    time_list = []
    for (image_path_m, dt) in considered_list:
        match_obj = re.search('([0-9]*).png', image_path_m)
        if match_obj:
            digits = len(match_obj.group(1))
            store_name = save_path + 'image' + '0'* (4 - digits) + match_obj.group(1) + '.png'
        else:
            print('Error: image to be processed {} in wrong format'.format(image_path_m))
            return
        
        print('Processing image {}'.format(image_path_m))
        ping_pong_tracker.get_new_image(image_path=image_path_m)
        time_start = time.time()
        if args.method == 'particle':
            ping_pong_tracker.propagate_particles(dt=dt)
            ping_pong_tracker.update_particles()
            ping_pong_tracker.generate_processed_frame(
                particles=ping_pong_tracker.current_state, show=args.show_particles,
                save=args.save_frames, store_name=store_name)
        elif args.method == 'hough':
            ping_pong_tracker.track_ball_hough(show=args.show_particles,
                save=args.save_frames, store_name=store_name,
                target_radius=args.target_radius, dt=dt,
                frames_to_process=frames_to_process)
        time_dt = time.time() - time_start
        print('time_dt: {}'.format(time_dt))
        time_list.append(time_dt)

    print('Mean computation time per frame: {}s'.format(np.mean(time_list)))


if __name__ == '__main__':
    main()
