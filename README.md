# mkcast

A tool for creating GIF screencasts of a terminal, with key presses overlaid.

![](demo.gif)

Dependencies: `wmctrl`, `byzanz-record` (slightly patched `screenkey` already bundled)

Usage: ./mkcast WINNAME DURATION [COMMAND (optional)]  
Usage: ./newcast [MKCAST ARGS]

Examples:

    # cast the window titled "Terminal" for 10 seconds, running the "reset"
    # command first
    ./mkcast Terminal 10 -c reset

    # equivalent to the above, but creates a new terminal for you and finishes
    # when the terminal exits instead of after a certain amount of time
    ./newcast -c reset

Suggested use: symlink `mkcast` and `newcast` in `/usr/local/bin`, and simply type (in GNOME) `Alt+F2 newcast Enter` for a quick mini-cast. This even allows you to set up a `gnome-terminal` profile called "mkcast," letting you automatically start a command when it opens (such as `vim`), customize the size or colors of the new terminal that is created, etc.

Only tested on GNOME on Ubuntu so far.

The name has a double meaning: **m**ini-**k**ey-**cast**, or **m**a**k**e cast (like mkdir).
