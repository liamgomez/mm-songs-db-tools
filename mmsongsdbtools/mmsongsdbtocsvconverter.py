#!/usr/bin/env python

import csv
import json
import logging
import os
import locale

import hdf5_getters

from pprint import pprint

logger = logging.getLogger(__name__)


class MMSongsDbToCsvConverter(object):
    """Helper object for reading hdf5 files and writing the results to a csv

    Sample usage:

        converter = MMSongsDbToCsvConverter('mmsongsdb.csv', ['artist_name', 'tempo'])
        converter.convert_directory('.')
    """
    def __init__(self, output_path, attrs_to_save=None):
        self.output_path = output_path
        self.attrs_to_save = attrs_to_save
        self.getters = None
        self.conversion_complete = 0

    def _get_getters(self, h5):
        all_getters = filter(lambda key: key[:4] == 'get_' and key != 'get_num_songs',
                             hdf5_getters.__dict__.keys())
        if not self.attrs_to_save:
            return sorted(all_getters)
        getters = []
        for attr in self.attrs_to_save:
            attr_getter = 'get_%s' % attr
            # Sanity
            if attr_getter in all_getters:
                getters.append(attr_getter)
            else:
                logger.error("No such attr! %s", attr_getter)
        return getters

    def _handle_h5_file(self, filename):
        h5 = hdf5_getters.open_h5_file_read(filename)
        num_songs = hdf5_getters.get_num_songs(h5)
        if not self.getters:
            self.getters = self._get_getters(h5)
            getter_row = [getter[4:] for getter in self.getters]
            self.writer.writerow(getter_row)
        for i in xrange(num_songs):
            result = []
            for getter in self.getters:
                hdf5_getter = getattr(hdf5_getters, getter)
                value = hdf5_getter(h5, i)
                if value.__class__.__name__ == 'ndarray':
                    # Special case for ndarray types
                    value = json.dumps(value.tolist())
                result.append(value)
            self.writer.writerow(result)
        h5.close()

    def _convert_directory(self, directory):
        """Internal function, for recursion
        """
        if not os.path.exists(directory):
            raise Exception("Directory %s doesn't exist, are you sure this is what you're looking for?" % directory)

        self.dirnames_seen.add(directory)
        for root, dirnames, filenames in os.walk(directory):
            dirnames.sort()
            filenames.sort()

            filenames = filter(lambda filename: filename.endswith('.h5'), filenames)

            self.conversion_complete += len(filenames) 
            count_string = "{:,}".format(self.conversion_complete)
            logger.info("_convert_directory() for dir %s with %s h5 files... Total converted: %s", root, len(filenames), count_string)

            for filename in sorted(filenames):
                trackid = os.path.splitext(filename)[0]
                destination_path = os.path.join(self.output_path, os.path.relpath(root, self.base_dir))
                if not os.path.exists(destination_path):
                    os.makedirs(destination_path)
                with open(os.path.join(destination_path, trackid) + ".csv", 'w') as self.fp:
                    self.writer = csv.writer(self.fp)
                    self._handle_h5_file(os.path.join(root, filename))

            dirnames = [os.path.join(root, dirname) for dirname in dirnames]
            dirnames = filter(lambda dirname: dirname not in self.dirnames_seen, dirnames)

    def convert_directory(self, directory):
        """External function

        Wo we can:
            - set up ish beforehand
            - close ish down when we're done
            - report how we did when we're done
        """

        logger.info("Running MMSongsDbToCsvConverter on %s - saving to %s",
                    directory,
                    self.output_path)
        self.base_dir = directory
        self.dirnames_seen = set()

        self._convert_directory(directory)
        logger.info("%s dirnames seen", len(self.dirnames_seen))
