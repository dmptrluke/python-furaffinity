class LoginError(Exception):
    """ Could not login to the server. """
    pass


class NotLoggedInError(Exception):
    """ Cannot properly interact with Fur Affinity unless you are logged in. """
    pass


class MaturityError(Exception):
    """ Cannot access that submission on this account because of maturity filter. """
    pass


class SubmissionNotFoundError(Exception):
    """ Could not find that submission. It has either been taken down, or does not exist yet. """
    pass


class AccessError(Exception):
    """ For some unknown reason Fur Affinity would not allow access to a submission. Try again. """
    pass


class SubmissionFileNotAccessible(Exception):
    """ Could not find/download the submission file. """
    pass


class IPBanError(Exception):
    """ You appear to be IP banned. This is not good. """
    pass
