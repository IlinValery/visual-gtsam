import os
from google_drive_downloader import GoogleDriveDownloader as gdd
from datetime import timedelta

from visual_gtsam.dataset.structures import ImuSequence, ImageSequence, Image, Imu


class Dataset(object):
    _image_sequence: ImageSequence
    _imu_sequence: ImuSequence

    def __init__(self, file_id='1XyRTmIfan7irlVnXYPh_M-2KgJLNDpl_', main_dir='downloads',
                 imu_json_filename='imus_data.json', image_dir='images', image_json_filename='image_data.json'):
        self._file_id = file_id
        self._main_dir = main_dir
        self._imu_json_filename = imu_json_filename
        self._image_dir = image_dir
        self._image_json_filename = image_json_filename

        self._is_downloaded = False
        self._download_dataset(file_id)
        self._read_dataset()

    def _download_dataset(self, file_id):
        path_to_images = "./{0}/{1}".format(self._main_dir, self._image_dir)
        if not os.path.exists(path_to_images):
            print("Downloading dataset")
            os.makedirs(self._main_dir, exist_ok=True)
            gdd.download_file_from_google_drive(file_id=file_id,
                                                dest_path='./{}/gt_dataset.zip'.format(self._main_dir),
                                                unzip=True)
            os.remove('./{}/gt_dataset.zip'.format(self._main_dir))
            self._is_downloaded = True
            print("Dataset was downloaded")
        else:
            self._is_downloaded = True
            print("Dataset is ready")

    def _read_dataset(self):
        self._imu_sequence = ImuSequence(self._main_dir, self._imu_json_filename)
        self._image_sequence = ImageSequence(self._main_dir, self._image_dir, self._image_json_filename)

    def get_image_sequence(self) -> ImageSequence:
        return self._image_sequence

    def get_imu_sequence(self):
        return self._imu_sequence

    def get_statistic(self):
        msg = "Total amount of IMU values is {}\nTotal amount of Images is {}".format(self._imu_sequence.get_length(),
                                                                                      self._image_sequence.get_length())
        return msg

    def get_imu_statistic(self):
        return self._imu_sequence.get_all_velocity(), self._imu_sequence.get_all_acceleration()

    def get_next_image(self) -> Image:
        return self._image_sequence.get_next()

    def get_next_imu(self) -> Imu:
        return self._imu_sequence.get_next()

    def get_next_pair(self) -> (Image, Imu):
        image = self.get_next_image()
        imu = self.get_next_imu()
        while abs(image.get_time() - imu.get_time()) > timedelta(milliseconds=10):
            try:
                imu = self.get_next_imu()
            except StopIteration:
                self.reset()
        return image, imu

    def reset(self):
        self._imu_sequence.reset()
        self._image_sequence.reset()
