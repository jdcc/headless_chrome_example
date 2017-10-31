Headless Chrome Example
=======================

Description
-----------

This is a simple example of using the headless feature of Google
Chrome/Chromium released somewhere around version 58.

`client.py` is a barebones Python interface to a Chrome instance. This is an
asynchronous interface, mainly because it relies on websockets to communicate
with the headless Chrome instance.

`visit.py` is a simple command line script for fetching a screenshot of a URL
through the headless client, optionally over a VPN connection.

Each instance of the client is isolated from all other instances. A temporary
user data directory is created and destroyed on every request, and the debugger
ports used to communicate with the client instance are chosen at random.

Requirements
------------

You'll need Google Chrome or Chromium >= v58.
`pip install -r requirements.txt` should take care of the rest.

Running
-------

Make sure the correct path to the Chrome executable is either changed in
`client.py` or passed in.

Then you should just be able to run:
`python visit.py "https://cyber.harvard.edu/"`

Screenshots will be saved in the `results` folder.

Tested Versions
---------------

This has been tested with Python 3.6 on Xubuntu 17.04 with Google Chrome versions
58-62.

Licence
-------

See LICENCE

Copyright
---------

Copyright 2017 President and Fellow of Harvard College
