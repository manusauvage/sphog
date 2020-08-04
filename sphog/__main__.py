"""
Sphog - Static Photo Gallery
----

A simple tool to quickly generate static photo galleries

:copyright: (c) 2020 Emmanuel le Chevoir.
:license: GPLv3, see LICENSE for more details.
"""

import os
import sys


if __name__ == '__main__':
    sys.path.insert(1, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))

    from sphog.app import main
    main()

