import datetime  # For working with dates
import re
from typing import List

import dateutil.parser  # For parsing dates lazily

from .errors import *
from .misc import clean, FAComment, FAFile

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
        self._comments = []

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
    def title_safe(self) -> str:
        """
        Returns the (sanitized) title of the submission.
        """
        title = NAME_UPLOADER_REGEX.match(self.soup.title.string).group(1)
        return clean(title, safe=True)

    @property
    def uploader(self) -> str:
        """
        Returns the uploader of the submission.
        """
        uploader = NAME_UPLOADER_REGEX.match(self.soup.title.string).group(2)
        return clean(uploader, safe=True)

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
    def time(self) -> datetime.datetime:
        """
        Returns a UTS datetime object with timezone information and everything.
        """
        # tip of the day - don't use dateparser
        # dateutil.parse is much faster
        return dateutil.parser.parse(self.time_raw)

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
    def favorite_count(self) -> int:
        """
        Returns the current amount of favorites the submission has, as an int.
        """
        block = self.soup.find("div", class_="submission-artist-stats").text.split('|')
        return int(block[1])

    @property
    def comment_count(self) -> int:
        """
        Returns the current amount of comments the submission has, as an int.
        """
        block = self.soup.find("div", class_="submission-artist-stats").text.split('|')
        return int(block[2])

    @property
    def view_count(self) -> int:
        """
        Returns the current amount of views the submission has, as an int.
        """
        block = self.soup.find("div", class_="submission-artist-stats").text.split('|')
        return int(block[0])

    @property
    def rating(self) -> str:
        """
        Returns the age rating of the submission in lowercase unicode.
        """
        rating = self.soup.find("span", class_="rating-box").text
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

    @property
    def comments(self):
        if not self._comments:
            for x in self.soup.find_all('div', class_="comment_container"):
                _id = x.get('id')[4:]
                _depth = abs(int(x.get('style')[6:-1]) - 100) // 3
                _author = clean(x.find('strong', class_="comment_username").text)
                _text = clean(x.find('div', class_="comment_text").get_text())

                self._comments.append(FAComment(_id, _depth, _author, _text))

        return self._comments

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
