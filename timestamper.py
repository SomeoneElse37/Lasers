"""
This script simply copies stdin to stdout line by line, with the exact time between when
the script was started to when the line was received prepended to each line.

I recommend running this script from the command line and using your shell to redirect the output to a file. Eg:
python timestamper.py > log.txt
"""

import datetime

starttime = datetime.datetime.now()

while True:
    s = input()
    print(datetime.datetime.now() - starttime, " ", s)





