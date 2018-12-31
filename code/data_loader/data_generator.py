import numpy as np
import os
import sys
import pandas as pd
from PIL import Image
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
import re


class DataGenerator:
    """A class that implements an iterator to load the data. It uses  as an
    environmental variable the data folder and then loads the necessary files
    (labels and images) and starts loading the data
    """

    def __init__(self, config):
        """The constructor of the DataGenerator class. It loads the training
        labels and the images.

        Parameters
        ----------
            config: dict
                a dictionary with necessary information for the dataloader
                (e.g batch size)
        """
        np.random.seed(42)
        cwd = os.getenv("DATA_PATH")
        if cwd is None:
            print("Set your DATA_PATH env first")
            sys.exit(1)
        self.config = config
        # Read csv file
        tmp = pd.read_csv(os.path.abspath(cwd + 'train.csv'),
                          delimiter=',', engine='python')
        # A vector of images id.
        image_ids = tmp["Id"]
        self.n = len(image_ids)
        # for each id sublist of the 4 filenames [batch_size, 4]
        self.filenames = np.asarray([[
            cwd + '/train/' + id + '_' + c + '.png'
            for c in ['red', 'green', 'yellow', 'blue']
        ] for id in image_ids])
        # Labels
        self.labels = tmp["Target"].values
        # To one-hot representation of labels
        # e.g. before e.g. ['22 0' '12 23 0']
        # after split [['22', '0'], ['12', '23', '0']]
        # after binarize it is one hot representation
        binarizer = MultiLabelBinarizer(classes=np.arange(28))
        self.labels = [[int(c) for c in l.split(' ')] for l in self.labels]
        self.labels = binarizer.fit_transform(self.labels)
        # Compute class weigths
        self.class_weights = np.reshape(1/np.sum(self.labels, axis=0), (1, -1))
        # Build a validation set
        try:
            self.train_filenames, self.val_filenames,\
                self.train_labels, self.val_labels = train_test_split(
                    self.filenames, self.labels,
                    test_size=self.config.val_split,
                    random_state=42)
        except AttributeError:
            print('WARN: val_split not set - using 0.2')
            self.train_filenames, self.val_filenames,\
                self.train_labels, self.val_labels = train_test_split(
                    self.filenames, self.labels,
                    test_size=0.2, random_state=42)
        self.n_train = len(self.train_labels)
        self.n_val = len(self.val_labels)
        print('Size of training set is {}'.format(self.n_train))
        print('Size of validation set is {}'.format(self.n_val))
        # Number batches per epoch
        self.train_batches_per_epoch = int(
            (self.n_train - 1) / self.config.batch_size) + 1
        self.val_batches_per_epoch = int(
            (self.n_val - 1) / self.config.batch_size) + 1
        self.all_batches_per_epoch = int(
            (self.n - 1) / self.config.batch_size) + 1

    def batch_iterator(self, type='all'):
        """
        Generates a batch iterator for the dataset for one epoch.
        Args:
            type: 'all' for whole dataset batching (i.e. for CV for baseline)
                  'train' for training set batching
                   'val' for validation batching
        Example:
            data = DataGenerator(config)
            training_batches = data.batch_iterator('train')
            val_batches = data.batch_iterator('val')
            all_batches = data.batch_iterator('all')
        """
        if type == 'all':
            filenames = self.filenames
            labels = self.labels
            num_batches_per_epoch = self.all_batches_per_epoch
        elif type == 'train':
            filenames = self.train_filenames
            labels = self.train_labels
            num_batches_per_epoch = self.train_batches_per_epoch
        elif type == 'val':
            filenames = self.val_filenames
            labels = self.val_labels
            num_batches_per_epoch = self.val_batches_per_epoch
        else:
            print('Wrong type argument for batch_iterator')
            exit(1)
        # Shuffle the data at each epoch
        n = len(labels)
        shuffle_indices = np.random.permutation(np.arange(n))
        shuffled_filenames = filenames[shuffle_indices]
        shuffled_labels = labels[shuffle_indices]
        for batch_num in range(num_batches_per_epoch):
            start_index = batch_num * self.config.batch_size
            end_index = min((batch_num + 1) * self.config.batch_size, n)
            batchfile = shuffled_filenames[start_index:end_index]
            batchlabel = shuffled_labels[start_index:end_index]
            batchimages = np.asarray(
                [[np.asarray(Image.open(x)) for x in y] for y in batchfile])
            yield batchimages, batchlabel

    def set_batch_iterator(self, type='all'):
        train_iterator = self.batch_iterator(type=type)
        self.train_iterator = train_iterator


class DataTestLoader:
    """A class that implements an iterator to load the data. It uses  as an
    environmental variable the data folder and then loads the necessary files
    (labels and images) and starts loading the data
    """

    def __init__(self, config):
        """The constructor of the DataTestLoader class. It loads the testing images.

        Parameters
        ----------
            config: dict
                a dictionary with necessary information for the dataloader
                (e.g batch size)
        """
        cwd = os.getenv("DATA_PATH")
        if cwd is None:
            print("Set your DATA_PATH env first")
            sys.exit(1)
        self.config = config
        list_files = [f for f in os.listdir(cwd + '/test/')]
        self.image_ids = list(
            set([
                re.search(r'(?P<word>[\w|-]+)\_[a-z]+.png', s).group('word')
                for s in list_files
            ]))
        self.n = len(self.image_ids)
        # for each id sublist of the 4 filenames [batch_size, 4]
        self.filenames = np.asarray([[
            cwd + 'test/' + id + '_' + c + '.png'
            for c in ['red', 'green', 'yellow', 'blue']
        ] for id in self.image_ids])

    def batch_iterator(self):
        """
        Generates a batch iterator for the dataset.
        """
        num_batches_per_epoch = int((self.n - 1) / self.config.batch_size) + 1
        for batch_num in range(num_batches_per_epoch):
            start_index = batch_num * self.config.batch_size
            end_index = min((batch_num + 1) * self.config.batch_size, self.n)
            batchfile = self.filenames[start_index:end_index]
            batchimages = np.asarray(
                [[np.asarray(Image.open(x)) for x in y] for y in batchfile])
            yield batchimages


if __name__ == '__main__':
    # just for testing
    from bunch import Bunch
    config_dict = {'batch_size': 32}
    config = Bunch(config_dict)
    TrainingSet = DataGenerator(config)
    """
    all_batches = TrainingSet.batch_iterator()
    for batch_x, batch_y in all_batches:
        print(np.shape(batch_x))   # (32, 4, 512, 512)
        print(np.shape(batch_y))
    """
    TestLoader = DataTestLoader(config)
    all_test_batches = TestLoader.batch_iterator()
    for batch_x in all_test_batches:
        print(np.shape(batch_x))  # (32, 4, 512, 512)