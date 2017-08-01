import hashlib  # To hash images and files
import os  # For working with paths
import re

import attr  # For useful tiny classes.
import requests

from .errors import SubmissionFileNotAccessible


# Functions for... functionality.
def clean(text, safe=False, separator=" "):
    """ Takes a string and cleans it up. """
    if safe:
        text = re.sub(r"[^0-9a-zA-Z-.,_ ]", '', text)

    return separator.join(text.strip().split())


# Useful tiny classes for passing data around.
@attr.s
class FAResult:
    id = attr.ib()
    kind = attr.ib()


@attr.s
class FAComment:
    id = attr.ib()
    depth = attr.ib()
    author = attr.ib()
    text = attr.ib()


class FAFile:
    def __init__(self, url):
        self._url = url
        self._local_path = None

    def download(self, destination: str, replace=False, skip=False):
        """
        Downloads the submission to the specified location. The image path is relative to the execution folder.
        If a file extension is provided, it will be discarded.

        TODO: Maybe work out the file format from magic bytes and save the file based on it? Right now we just
        use the extension from the original URL.

        Args:
            destination (str)
        """
        try:
            r = requests.get(self._url, stream=True)
        except requests.ConnectionError:
            raise SubmissionFileNotAccessible

        # remove extension if one exists
        destination = os.path.splitext(destination)[0]

        # ensure destination exists, make temporary path for downloading
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        path_final = destination + '.' + self.extension
        path_tmp = destination + '~PART'

        if os.path.exists(path_final):
            if replace and skip:
                raise RuntimeError("Download called with both skip and replace. You can't do that.")
            elif replace:
                pass
            elif skip:
                return
            else:
                raise FileExistsError("File already exists: {}".format(path_final))

        # if os.path.exists(path_tmp):
        #     raise FileExistsError("Temporary file already exists: {}".format(path_tmp))

        try:
            with open(path_tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

            # rename the file to the final path
            os.rename(path_tmp, path_final)
        finally:
            # make sure we've cleaned up any messes if something went wrong
            try:
                os.remove(path_tmp)
            except OSError:
                pass

        # store the path we downloaded to to make calculate_hash() faster
        self._local_path = path_final

    def calculate_hash(self, algorithm='sha256') -> bytes:
        """
        Retrieves the sha256 hash of the submission. If the submission has previously been downloaded with the
        download() function in this FASubmission instance, it will retrieve the hash using that existing file.
        If not, file will be downloaded, hashed, and discarded.
        """
        if algorithm not in hashlib.algorithms_available:
            raise ValueError("Requested hash algorithm is not available.")

        hash_ = getattr(hashlib, algorithm)()

        if self._local_path and os.path.exists(self._local_path):
            with open(self._local_path, "rb") as f:
                hash_.update(f.read())
        else:
            try:
                path = self._url
                r = requests.get(path, stream=True)
            except requests.ConnectionError:
                raise SubmissionFileNotAccessible

            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    hash_.update(chunk)

        return hash_.digest()

    @property
    def url(self) -> str:
        """
        Returns the url of the file.
        """
        return self._url

    @property
    def filename(self) -> str:
        """
        Returns the filename of the file, extracted from the url.
        """
        return os.path.basename(self._url)

    @property
    def extension(self) -> str:
        """
        Returns extension of the file.
        """
        return os.path.splitext(self._url)[1][1:]
