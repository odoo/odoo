This directory should contain all test scripts.

All test scripts should be named like test_*.py, where * describes which
parts of the ReportLab toolkit are being tested (see sample test scripts).

The test scripts are expected to make use of the PyUnit test environment
named unittest (see pyunit.sourceforge.net). For convenience this comes
bundled with the ReportLab toolkit in the reportlab.test subpackage.

As of now, this folder has a flat structure, but it might be restructured
in the future as the amount of tests will grow dramatically.

The file runAll.py begins by deleting any files with extension ".pdf" or
".log" in the test directory, so you can't confuse old and current
test output.  It then loops over all test scripts following the 
aforementioned pattern and executes them.

Any PDF or log files written should be examined, at least before
major releases.  If you are writing tests, ensure that you only
leave behind files which you intend a human to check.
