import datetime  # For working with dates
import hashlib  # To hash images and files
import os  # For working with paths
import re

from typing import List

import requests
import dateutil.parser  # For parsing dates lazily

from .errors import *
from .misc import clean


NAME_UPLOADER_REGEX = re.compile(r'(.+) by (.+) --')
CATEGORY_THEME_REGEX = re.compile(r" ?(.+) > (.+)")

KEYWORDS_REGEX = re.compile(r"/search/@keywords .+")


class FASubmission:
    """
    Represents a single fur affinity submission.
    """

    def __init__(self, soup, identifier: str):
        """
        Initiates the FASubmission object based on a soup object passed to it.
        """
        self.local_path = None
        self.id = identifier
        self.soup = soup

        self._file = None
        self._thumb = None

    @property
    def file(self):
        if not self._file:
            url = "https:" + self.soup.find('a', text="Download").get('href')
            self._file = FAFile(url)

        return self._file

    @property
    def thumb(self):
        if not self._thumb:
            url = "https:" + self.soup.find('img', id="submissionImg").get('data-preview-src')
            self._thumb = FAFile(url)

        return self._thumb

    @property
    def title(self) -> str:
        """
        Returns the title of the submission.
        """
        title = NAME_UPLOADER_REGEX.match(self.soup.title.string).group(1)
        return title

    @property
    def uploader(self) -> str:
        """
        Returns the uploader of the submission.
        """
        uploader = NAME_UPLOADER_REGEX.match(self.soup.title.string).group(2)
        return uploader

    @property
    def description(self) -> str:
        """
        Returns the description of the submission as plain text
        """
        description = self.soup.find('div', class_='submission-description').get_text()
        return clean(description)

    @property
    def description_html(self) -> str:
        """
        Returns the description of the submission as HTML
        """
        description_html = self.soup.find('div', class_='submission-description').prettify()
        return description_html

    # upload time functions
    @property
    def time_raw(self) -> str:
        """
        Returns the time the submission was posted, as a string, in lowercase unicode.
        NOTE: This is gotten directly from the image information, unparsed.
        """
        container = self.soup.find("span", class_="popup_date")
        _time = container.string
        if _time[-3:] == "ago":
            _time = container.get("title")

        return clean(_time)

    @property
    def time_parsed(self) -> datetime.datetime:
        """
        Returns a UTS datetime object with timezone information and everything.
        """
        # tip of the day - don't use dateparser
        # dateutil.parse is much faster
        return dateutil.parser.parse(self.time_raw)

    @property
    def time_formatted(self) -> str:
        """
        Retrieves the last-modified string from the header, as a string in UNIX time format.
        NOTE: You need to have parsed the image file before retrieving this.
        FURTHER NOTE: This function has never done what it says it does. Ever.
                      I just found it like this. It takes the normal date and
                      outputs it in a format that looks like a timestamp.
                      I should remove it.
        """
        _time = self.time_parsed
        formatted = _time.strftime("%d/%m/%Y %H:%M")
        return clean(formatted)

    # sub info
    @property
    def category(self) -> str:
        """
        Returns the category of the submission.
        """
        bit = self.soup.find("strong", text="Category:").next_sibling
        category = CATEGORY_THEME_REGEX.match(bit).group(1)
        return clean(category)

    @property
    def theme(self) -> str:
        """
        Returns whatever theme is, from the submission.
        """
        bit = self.soup.find("strong", text="Category:").next_sibling
        theme = CATEGORY_THEME_REGEX.match(bit).group(2)
        return clean(theme)

    @property
    def species(self) -> str:
        """
        Returns the species depicted in the submission.
        """
        species = self.soup.find("strong", text="Species:").next_sibling
        return clean(species)

    @property
    def gender(self) -> str:
        """
        Returns the gender depicted in the submission.
        """
        gender = self.soup.find("strong", text="Gender:").next_sibling
        return clean(gender)

    # stats/rating
    @property
    def favorites(self) -> int:
        """
        Returns the current amount of favorites the submission has, as an int.
        """
        favs = clean(self.soup.find("h3", text="Favs").find_next("span").text)
        return int(favs.strip())

    @property
    def comments(self) -> int:
        """
        Returns the current amount of comments the submission has, as an int.
        """
        comments = clean(self.soup.find("h3", text="Comments").find_next("span").text)
        return int(comments.strip())

    @property
    def views(self) -> int:
        """
        Returns the current amount of views the submission has, as an int.
        """
        views = clean(self.soup.find("h3", text="Views").find_next("span").text)
        return int(views.strip())

    @property
    def rating(self) -> str:
        """
        Returns the age rating of the submission in lowercase unicode.
        """
        rating = self.soup.find("div", class_="rating-box").text
        return clean(rating)

    @property
    def keywords(self) -> List[str]:
        """
        Returns the keywords list of the submission.
        """
        keywords = []

        for a in self.soup.find_all("a", href=KEYWORDS_REGEX):
            keywords.append(clean(a.string))

        return keywords

    @property
    def tagged_users(self) -> List[str]:
        """
        Returns the users mentioned in the description of the submission.
        """
        # Looks for "iconusername" and "linkusername" link classes and retrieve the username off of the link.
        tagged = []
        for user in self.soup.find_all("a", class_="iconusername"):
            tagged.append(clean(user.get('href')[6:]))

        return tagged

    def check_errors(self):
        """
        Raises an exception based on the access error or lack thereof.
        This is usually called by FurAffinity.get_submission(), so you shouldn't have to touch it.
        """
        if self.soup.title.string == "System Error":
            raise SubmissionNotFoundError
        elif "Your IP address has been banned." in str(self.soup):
            raise IPBanError
        elif "This submission contains Mature or Adult content" in str(self.soup):
            raise MaturityError
        elif "You are not allowed to view this image" in str(self.soup):
            raise AccessError

    @property
    def html(self) -> str:
        return self.soup.prettify()


class FAFile:
    def __init__(self, url):
        self._url = url
        self._local_path = None

    def download(self, destination: str):
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
        path_tmp = destination + '~PART'

        with open(path_tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        # rename the file to the final path
        path_final = destination + '.' + self.file_extension
        os.rename(path_tmp, path_final)

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
