import attr  # For useful tiny classes.
import re


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
