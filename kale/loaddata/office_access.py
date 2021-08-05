import logging
import os

from kale.loaddata.dataset_access import DatasetAccess
from kale.loaddata.multi_domain import MultiDomainImageFolder
from kale.prepdata.image_transform import get_transform
from kale.utils.download import download_file_by_url

url = "https://github.com/sz144/data/raw/main/image_data/office/"
DOMAINS = ["amazon", "caltech", "dslr", "webcam"]
office_transform = get_transform("office")


class OfficeAccess(MultiDomainImageFolder, DatasetAccess):
    """Common API for office dataset access

        Args:
            root (string): root directory of dataset
            transform (callable, optional): A function/transform that takes in an PIL image and returns a transformed
                version. Defaults to office_transform.
            download (bool, optional): Whether to allow downloading the data if not found on disk. Defaults to False.
        """

    def __init__(self, root, transform=office_transform, download=False, **kwargs):
        # init params
        if download:
            self.download(root)
        super(OfficeAccess, self).__init__(root, transform=transform, **kwargs)

    @staticmethod
    def download(path):
        """Download dataset."""
        if not os.path.exists(path):
            os.makedirs(path)
        for domain_ in DOMAINS:
            filename = "%s.zip" % domain_
            data_path = os.path.join(path, filename)
            if os.path.exists(data_path):
                logging.info(f"Data file {filename} already exists.")
                continue
            else:
                data_url = "%s/%s" % (url, filename)
                download_file_by_url(data_url, path, filename, "zip")
                # zip_file = zipfile.ZipFile(data_path, "r")
                # zip_file.extractall(path)
                logging.info(f"Download {data_url} to {data_path}")

        logging.info("[DONE]")
        return


class Office31(OfficeAccess):
    def __init__(self, root, **kwargs):
        """Office-31 Dataset. Consists of three domains: 'amazon', 'dslr', and 'webcam', with 31 image classes.

        Args:
            root (string): path to directory where the office folder will be created (or exists).
        """
        sub_domain_set = ["amazon", "dslr", "webcam"]
        super(Office31, self).__init__(root, sub_domain_set=sub_domain_set, **kwargs)


class OfficeCaltech(OfficeAccess):
    def __init__(self, root, **kwargs):
        """Office Caltech 10 Dataset. Consists of four domains: 'amazon', 'caltech', 'dslr', and 'webcam',
            with 10 overlapped classes.

        Args:
            root (string): path to directory where the office folder will be created (or exists).
        """
        sub_class_set = [
            "mouse",
            "calculator",
            "back_pack",
            "keyboard",
            "monitor",
            "projector",
            "headphones",
            "bike",
            "laptop_computer",
            "mug",
        ]
        super(OfficeCaltech, self).__init__(root, sub_class_set=sub_class_set, **kwargs)
