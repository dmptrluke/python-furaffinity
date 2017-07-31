import itertools  # For count
import re  # For finding stuff in the soup.
import time  # For sleeping

import bs4  # For parsing web pages.
import requests  # For accessing pages over the internet.

from typing import List

from .errors import NotLoggedInError, LoginError
from .misc import FAResult, clean
from .submission import FASubmission

GALLERY_CLASS_REGEX = re.compile(r"r-([a-z]+) t-([a-z]+)")
WATCHLIST_REGEX = re.compile(r"/unwatch/(.*)/\?key=[0-9a-f]*")

WAIT_TIME = 1


class FurAffinity:
    """
    Represents Fur Affinity.
    """

    def __init__(self, useragent=None, session=None):
        """
        Initiates the FurAffinity object
        """
        self.session = session or requests.Session()
        self.logged_in = False

        if useragent:
            self.session.headers["User-Agent"] = useragent


    ###
    # Authentication
    ###

    def login(self, username, password) -> bool:
        """
        Logs into a FurAffinity account identified by username and password.

        Args:
            username (str): Username of account to log in as.
            password (str): Password of account to log in as.
        Returns:
            bool: True if login successful.
        """
        raise NotImplementedError

    def login_cookies(self, cookies: dict):
        """
        Logs into a FurAffinity account identified by cookies.

        Args:
            cookies (dict): cookies of account to log in as.
        Returns:
            True if login successful.
        """
        self.session.cookies.update(cookies)

        if self.check_login():
            self.logged_in = True
        else:
            raise LoginError("Bad cookies")

    def check_login(self) -> bool:
        """
        Returns whether you are logged in or not.
        """
        response = self.session.get("https://www.furaffinity.net/")
        soup = bs4.BeautifulSoup(response.text, "html.parser")
        user_link = soup.find("a", id="my-username")

        return not not user_link

    ###
    # User submissions
    ###

    def __get_user_submissions(self, sub_page: str, username: str, page=1, num_pages=1) -> List[FAResult]:
        """
        Returns list of users submissions in an arbitrary sub-page.
        Should only be used internally.
        """
        if not self.logged_in:
            raise NotLoggedInError

        results = []
        username = username.lower()

        end_page = page + num_pages
        while page < end_page:
            response = self.session.get(f"https://www.furaffinity.net/{sub_page}/{username}/{page}")
            soup = bs4.BeautifulSoup(response.text, "html.parser")

            if soup.find("div", id="no-images"):
                break
            else:
                submissions = soup.find(id='gallery-gallery').find_all("figure")

                for submission in submissions:
                    _id = int(submission.get("id")[4:])
                    kind = GALLERY_CLASS_REGEX.match(" ".join(submission.get("class")))[2]
                    results.append(FAResult(_id, kind))

            if page > 1:
                time.sleep(1)
            page += 1

        return results

    def get_user_gallery(self, username: str, **kwargs) -> List[FAResult]:
        """
        Returns list of submissions in an users gallery.
        """
        return self.__get_user_submissions("gallery", username, **kwargs)

    def get_user_scraps(self, username: str, **kwargs) -> List[FAResult]:
        """
        Returns list of submissions in an users scraps.
        """
        return self.__get_user_submissions("scraps", username, **kwargs)

    def get_user_submissions(self, username: str, **kwargs) -> List[FAResult]:
        """
        Returns list of submissions in an users gallery and scraps.
        """
        l = self.get_user_gallery(username, **kwargs)
        l.extend(self.get_user_scraps(username, **kwargs))
        return l

    def get_user_favorites(self, username: str, **kwargs) -> List[FAResult]:
        """
        Returns list of submissions in an users favorites.
        """
        return self.__get_user_submissions("favorites", username, **kwargs)

    get_user_favourites = get_user_favorites

    ###
    # "followed users" queue
    ###

    def get_queue(self, nuke=False, page=1, num_pages=1) -> List[FAResult]:
        """
        Returns list of submissions from the new submissions page.
        """
        if not self.logged_in:
            raise NotLoggedInError

        response = self.session.get("https://www.furaffinity.net/msg/submissions/old/")
        soup = bs4.BeautifulSoup(response.text, "html.parser")

        results = []

        if "There are no submissions to list" in str(soup):
            return results

        end_page = page + num_pages
        while page < end_page:
            submissions = soup.find(id='messagecenter-submissions').find_all("figure")

            for submission in submissions:
                _id = int(submission.get("id")[4:])
                kind = GALLERY_CLASS_REGEX.match(" ".join(submission.get("class")))[2]
                results.append(FAResult(_id, kind))

            # Find next page button
            next_page_link = soup.find("a", class_="more").get("href")
            if next_page_link.find("old@") >= 0:
                break

            response = self.session.get("https://www.furaffinity.net" + next_page_link)
            soup = bs4.BeautifulSoup(response.text, "html.parser")

            if page > 1:
                time.sleep(1)
            page += 1

        if nuke:
            self.nuke_queue()

        return results

    def nuke_queue(self):
        """
        Uses the 'nuke all submissions' button in the 'messagecenter'.
        This function does not seem to work. It may have never worked.
        """
        if not self.logged_in:
            raise NotLoggedInError

        print("Nuking submissions")
        data = {
            "messagecenter-action": "Nuke+all+Submissions"
        }

        self.session.post("https://www.furaffinity.net/msg/submissions/", data=data)

    ###
    # Searching
    ###

    def search(self, query, time_range="all", sort="relevancy", order="desc",
               page=1, num_pages=1, ratings=None, types=None) -> List[FAResult]:
        """
        Searches FurAffinity for submissions.

        Args:
            query (str): The string to search for.
            time_range (str, optional): the time range to search within (day, 3days, week, month, *all*)
            sort (str, optional): the criteria to sort results by (*relevancy*, date, popularity)
            order (str, optional): the order to sort by (asc, *desc*)
            page (int, optional): the page number to start searching at (default: 1)
            num_pages (int, optional): the number of pages to search for (default: 1)
            ratings (list, optional): which ratings to include in the search. [General, Mature, Adult]
            types (list, optional): which types to include. [Art, Flash, Photo, Music, Story, Poetry]

        Returns:
            A list of search results in (POST ID, POST TYPE) tuples.
        """

        if ratings is None:
            ratings = [1, 1, 1]
        if types is None:
            types = [1, 0, 1, 0, 0, 0]

        list_ = []
        end_page = page + num_pages

        form = {
            "q": query,
            "page": str(page),
            "perpage": "72",
            "order-by": sort,
            "order-direction": order,
            "range": time_range,

            "do_search": "Search",

            "rating-general": ratings[0] and "on" or None,
            "rating-mature": ratings[1] and "on" or None,
            "rating-adult": ratings[2] and "on" or None,

            "type-art": types[0] and "on" or None,
            "type-flash": types[1] and "on" or None,
            "type-photo": types[2] and "on" or None,
            "type-music": types[3] and "on" or None,
            "type-story": types[4] and "on" or None,
            "type-poetry": types[5] and "on" or None,

            "mode": "extended"
        }

        while page < end_page:
            form["page"] = str(page)
            response = self.session.post("https://www.furaffinity.net/search/", data=form)

            soup = bs4.BeautifulSoup(response.text, "html.parser")

            submissions = soup.find(id='gallery-search-results').find_all("figure")
            if not submissions:
                break

            # Not sure if this is useful. Just replicating what the actual site does.
            # del form["do_search"]
            # form["next_page"] = soup.find('input', attrs={'name': 'next_page'}).get('value')

            for submission in submissions:
                _id = int(submission.get("id")[4:])
                kind = GALLERY_CLASS_REGEX.match(" ".join(submission.get("class")))[2]
                list_.append(FAResult(_id, kind))

            if page > 1:
                time.sleep(WAIT_TIME)
            page += 1

        return list_

    def search_tags(self, *tags, **kwargs) -> List[FAResult]:
        """
        Searches FurAffinity for submissions tagged with one or more specified tags.

        Args:
            *tags: One or more tags to search for. Strings please.
            **kwargs: Extra options to pass to search().

        Returns:
            A list of search results in (POST ID, POST TYPE) tuples.
        """
        return self.search("@keywords " + " ".join(tags), **kwargs)

    ###
    # Submissions
    ###

    def get_submission(self, submission) -> FASubmission:
        """
        Returns a FASubmission object for a furaffinity submission identified
        by submission_id. Will raise an error if it cannot access the
        submission.

        Args:
            submission (int|str|FAResult): ID of submission

        Returns:
            FASubmission

        """

        if not self.logged_in:
            raise NotLoggedInError

        if type(submission) is FAResult:
            submission = submission.id
        submission = str(submission)

        response = self.session.get(f"https://www.furaffinity.net/view/{submission}/")
        soup = bs4.BeautifulSoup(response.text, "html.parser")

        submission = FASubmission(soup, submission)

        submission.check_errors()
        return submission

    ###
    # Misc account functions
    ###

    def get_watchlist(self) -> List[str]:
        """
        Returns a list of usernames, of the users on the logged in users watchlist.
        """
        if not self.logged_in:
            raise NotLoggedInError

        users = []

        for i in itertools.count(1):
            response = self.session.get("https://www.furaffinity.net/controls/buddylist/" + str(i))
            soup = bs4.BeautifulSoup(response.text, "html.parser")

            for user in soup.find_all("a", href=WATCHLIST_REGEX):
                username = clean(WATCHLIST_REGEX.match(user.get("href")).group(1))
                if username not in users:
                    users.append(username)
                else:
                    return users

    def get_account_settings(self) -> dict:
        """
        Returns a dict of account settings for the currently logged in account.
        """
        if not self.logged_in:
            raise NotLoggedInError

        response = self.session.get("https://www.furaffinity.net/controls/settings/")
        soup = bs4.BeautifulSoup(response.text, "html.parser")

        settings = {
            "fullname": soup.find("input", attrs={"name": "fullname"}).get("value"),
            "useremail": soup.find("input", attrs={"name": "fa_useremail"}).get("value"),
            "timezone": soup.find("select", attrs={"name": "timezone"}).find("option", selected="selected").get(
                "value"),
            # "timezone_dst":		soup.find("input", attrs={"name": "timezone_dst"}).get("checked") and "1" or None,

            "bdayday": soup.find("select", attrs={"name": "bdayday"}).find("option", selected="selected").get("value"),
            "bdaymonth": soup.find("select", attrs={"name": "bdaymonth"}).find("option", selected="selected").get(
                "value"),
            "bdayyear": soup.find("select", attrs={"name": "bdayyear"}).find("option", selected="selected").get(
                "value"),
            "viewmature": soup.find("select", attrs={"name": "viewmature"}).find("option", selected="selected").get(
                "value"),

            "style": soup.find("select", attrs={"name": "style"}).find("option", selected="selected").get("value"),
            "stylesheet": soup.find("select", attrs={"name": "stylesheet"}).find("option", selected="selected").get(
                "value")
        }

        # oldSettings["timezone_dst"]

        return settings

    def get_site_settings(self) -> dict:
        """
        Returns a dict of site settings for the currently logged in account.
        """
        if not self.logged_in:
            raise NotLoggedInError

        response = self.session.get("https://www.furaffinity.net/controls/site-settings/")
        soup = bs4.BeautifulSoup(response.text, "html.parser")

        settings = {
            "disable_avatars": soup.find("input", id="disable_avatars_yes").get("checked") and "1" or "0",
            "date_format": soup.find("input", id="switch-date-format-full").get("checked") and "1" or "0",
            "perpage": soup.find("select", id="select-preferred-perpage"
                                ).find("option", selected="selected").get("value"),
            "newsubmissions_direction":
                soup.find("select", id="select-newsubmissions-direction"
                         ).find("option", elected="selected").get("value"),
            "thumbnail_size":
                soup.find("select", id="select-thumbnail-size").find("option", selected="selected").get("value"),
            "hide_favorites": soup.find("select", id="hide-favorites").find("option", selected="selected").get("value"),
            "no_guests": soup.find("select", id="no-guests").find("option", selected="selected").get("value"),
            "no_notes": soup.find("select", id="no-notes").find("option", selected="selected").get("value")
        }

        return settings
