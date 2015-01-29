# mkcast

A tool for creating GIF screencasts of a terminal, with key presses overlaid.

![](demo.gif)

Dependencies: `wmctrl`, `byzanz-record` (slightly patched `screenkey` already bundled)

Usage: ./mkcast WINNAME DURATION [COMMAND (optional)]  
Usage: ./newcast [MKCAST ARGS]  
Usage: ./askcast

Examples:

    # cast the window titled "Terminal" for 10 seconds, running the "reset"
    # command first
    ./mkcast Terminal 10 -c reset

    # equivalent to the above, but creates a new terminal for you
    ./newcast 10 -c reset

    # asks for arguments to newcast, type ex. "10 -c reset"
    ./askcast

Suggested use: symlink `mkcast`, `newcast`, and `askcast` in `/usr/local/bin`, and simply type (in GNOME) `Alt+F2 askcast Enter` for a quick mini-cast.

screencast.conf format:

    {
        'timeout': 2.5,  # in seconds
        'position': 2,   # top=0, 1=middle, 2=bottom
        'size': 8,       # large=24, medium=12, small=8
        'mode': 1        # don't change this
    }

Only tested on GNOME on Ubuntu so far.
