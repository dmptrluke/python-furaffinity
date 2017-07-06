python-furaffinity
==================
A Python library for browsing, scraping and downloading content from Fur Affinity.
This project is still under heavy development, so don't expect it to be finished quite yet.

This requires **Python 3.6**. Your account must also be set to the **Beta** theme for this to work at all.

## How do I use this?
Proper documentation will be coming (eventually), but here is  a short demonstration script 
that should help you get the idea of what this library can do.
 
 ```python
""""
A demo script that searches FA for submissions tagged "cat" and "dancing",
 loops over them, and saves them to folders sorted by artist
"""
import furaffinity
import time

COOKIES = {
    "a": "YOUR A COOKIE FROM FA",
    "b": "YOUR B COOKIE FROM FA"
}

session = furaffinity.FurAffinity(useragent="python-furaffinity")
session.login_cookies(COOKIES)

results = session.search_tags("cat", "dancing")

for result in results:
    if not result.kind == "image":
        continue

    # get the FA submission
    submission = session.get_submission(result)

    # figure our where to save it
    location = f"./output/{submission.uploader}/{submission.file_name}"

    # save it
    submission.download(location)
    
    # be nice! don't thrash the servers
    time.sleep(1)
```

## License
**python-furaffinity** is licensed under the **MIT** license. The terms are as follows.

```
MIT License

Copyright (c) 2017 Luke R <me+opensouce@dmptr.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Parts of **python-furaffinity** are based off **[WTFPL](http://www.wtfpl.net/about/)** code from 
[anonymph/furaffinity-scraper-network](https://bitbucket.org/anonymph/furaffinity-scraper-network). 

Try not to break the servers.

