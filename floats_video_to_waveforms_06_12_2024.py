'''
This file contains function for converting videos to waveforms
NOTE: This script does NOT apply intrinsic matrices of the camera 
to adjust for distortion

Author: Gordon Doore
Created: 06/12/2024

Last Modified: 06/14/2024

'''
import cv2 
import numpy as np
import matplotlib.pyplot as plt
import orthorec_06_03_2024 as orth
from concurrent.futures import ThreadPoolExecutor


def rect_floats_video_to_waveform(rectified_video_path, ppm, num_stakes, 
                             arr_out_path = 'wave_measurements.npy',
                             graph_out_path = 'position_graphs.png', show= True):
    '''
    Converts a rectified video of floating objects to waveforms.
    
    Parameters:
    rectified_video_path (str): The path to the rectified video file.
    ppm (float): The pixels per meter conversion factor.
    num_stakes (int): The number of floating objects to track.
    arr_out_path (str, optional): The output path for the waveform measurements array. Defaults to 'wave_measurements.npy'.
    graph_out_path (str, optional): The output path for the position graphs. Defaults to 'position_graphs.png'.
    show (bool, optional): Whether to display the tracking frames. Defaults to True.
    
    Returns:
    numpy.ndarray: The waveform measurements array.
    '''
    
    position = track_objects_in_video(rectified_video_path,num_stakes, show = show)

    #convert position to real units: 
    position = position/ppm

    # Plot the y coordinates through time
    fig = plt.figure()
    for i in range(num_stakes):
        name = 'stake'+str(i)
        plt.plot(position[:,i,1],label = name)
    plt.xlabel('Time')
    plt.ylabel('Position (m)')
    plt.legend()
    fig.savefig(graph_out_path)

    np.save(arr_out_path,position)
    return position

def unrectified_to_rect_to_waveform(video_path, ppm, num_stakes,rect_path, 
                            arr_out_path = 'wave_measurements.npy',
                            graph_out_path = 'position_graphs.png', 
                            threshold_condition = lambda x: np.sum(x,axis=1)<300,
                            show = True):
    '''Converts an unrectified video of floating objects to waveforms.
    
    Parameters:
    video_path (str): The path to the rectified video file.
    ppm (float): The pixels per meter conversion factor.
    num_stakes (int): The number of floating objects to track.
    arr_out_path (str, optional): The output path for the waveform measurements array. Defaults to 'wave_measurements.npy'.
    graph_out_path (str, optional): The output path for the position graphs. Defaults to 'position_graphs.png'.
    threshold_condition (function): Function that is applied to ndarray which threhsolds based on some intrinsic value
    show (bool, optional): Whether to display the tracking frames. Defaults to True.
    
    Returns:
    numpy.ndarray: The waveform measurements array.
    '''
    #first we rectify our image:
    orth.rectify_video_by_gradation(video_path,rect_path, threshold_condition,show)
    return rect_floats_video_to_waveform(rect_path, ppm, num_stakes, arr_out_path, 
                             graph_out_path,show)

def track_objects_in_video(cap, num_stakes, show=False):
    """
    Tracks objects in a video.

    Args:
        video_path (str): Path to the video file.
        num_stakes (int): Number of objects to track.
        show (bool): If True, display the tracking process in real-time.

    Returns:
        np.ndarray: An array containing the positions of the tracked objects.
    """

    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read video frame.")
        return

    trackers = []
    for i in range(num_stakes):
        roi = cv2.selectROI("Select ROI", frame, False)
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        tracker = cv2.legacy_TrackerCSRT.create()
        trackers.append(tracker)
        tracker.init(frame, roi)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(total_frames)
    position = np.zeros((total_frames, num_stakes, 2))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1

        for i, tracker in enumerate(trackers):
            success, bbox = tracker.update(frame)
            if success:
                position[current_frame, i] = (bbox[0] + bbox[2] / 2, bbox[1] + bbox[3] / 2)  # Store the center position
                #draw bounding box on current_frame
                cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3])), (0, 0, 255), 2)
    
        if show:
            cv2.imshow('Tracking', frame)
            if cv2.waitKey(1) & 0xFF == 27:  # ESC key to break
                break

    cap.release()
    cv2.destroyAllWindows()
    return position

def unrectified_to_waveform(video_path, num_stakes, show = True):
    '''
    
    '''
    
    #load in video:
    cap = cv2.VideoCapture(video_path)

    # Read the first frame
    ret, frame = cap.read()

    #get the total frames:
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    #next, we extract the points of the gradations for n_stakes
    #for now we have the user select these points.
    all_points, all_lines = orth.define_stakes(frame,num_stakes)
    all_points = np.array(all_points)
    #assuming the user chooses points corresponding to the gradations
    #we use this to save the ppm for each stake:
    ppm = np.linalg.norm(all_points[:,0]-all_points[:,1],axis = 1)
    
    #after getting ppm, track each stake in the input space:
    
    positions = track_objects_in_video(cap, num_stakes, show = show)

    #apply derived ppm to the positions: 
    positions = positions/ppm#not sure if the axis work out written like this

    #save array
    return positions

    
if __name__ == '__main__':
    # floats_video_to_waveform('videos/noodle_float_move_rect.mp4',750,2)

    unrectified_path = 'videos/test_vid1.mp4'
    ppm = 375
    num_stakes = 2
    rect_path = 'videos/rectified_case.mp4'

    positions = unrectified_to_waveform(unrectified_path, num_stakes, show = True)

    # Plot the y coordinates through time
    fig = plt.figure()
    for i in range(num_stakes):
        name = 'stake'+str(i)
        plt.plot(positions[2:,i,1],label = name)
    plt.xlabel('Time')
    plt.ylabel('Position (m)')
    plt.legend()
    fig.savefig('graph.png')

    np.save('array.npy',positions[2:])