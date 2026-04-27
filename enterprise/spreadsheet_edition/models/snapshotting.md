
Vocabulary
----------

Revision = change = command: a change made to a spreadsheet by somebody
Snapshot: the state of a spreadsheet at a specific point in time. This point is time is embodied by the last revision of the spreadsheet.

Goal
----

The state of the spreadsheet can be computed by executing all the changes since the spreadsheet was created, in order. This works well but might be slow for spreadsheets with a lot of changes.
We could save a snapshot at any time, but this means that from this point, nobody could use the undo command to come back to a previous state: that previous state is lost.

Solutions
--------

To make a snapshot, we must make sure that there is only one person connected to a spreadsheet and that this person didn't do any command (thus cannot undo anything)

1) saving a snapshot while quitting
the hard part of this solution is to determine that there is a "last person active" on a spreadsheet and making him do the snapshot

2) saving a snapshot at regular interval
The hard part of this is to determine when and who can do a snapshot, knowing that anybody connected can still undo one of the last 100 commands he has done, and those commands might be undo themselves (this in virtually infinite until the first command of the spreadsheet)

3) saving a snapshot at opening
the hard part of this is to determine that a user is "the first to connect" on a spreadsheet.
This can be simplified if we say that "if no revision has been done for the last X hours, we can assume that all clients are disconnected or at least that they will not undo their changes and we can remove their ability to undo".a
--> as of 2021/04/15 we choose this solution as it is simple, feasible and doesn't remove a lot of the user experience.

4) never saving a snapshot
That is a simple solution that works well, but over time frequently used spreadsheet might take a long time (and a lot of memory) to open.
