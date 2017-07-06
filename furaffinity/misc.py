import attr  # For useful tiny classes.


# Functions for... functionality.
def clean(text):
    """ Takes a string and cleans it up. """
    return ' '.join(text.strip().split())


# Useful tiny classes for passing data around.
@attr.s
class FAResult:
    id = attr.ib()
    kind = attr.ib()
