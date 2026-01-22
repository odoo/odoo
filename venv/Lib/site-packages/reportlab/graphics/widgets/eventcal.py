#see license.txt for license details
#history https://hg.reportlab.com/hg-public/reportlab/log/tip/src/reportlab/graphics/widgets/eventcal.py
# Event Calendar widget
# author: Andy Robinson

__version__='3.3.0'
__doc__="""This file is a
"""

from reportlab.lib import colors
from reportlab.graphics.shapes import Rect, Drawing, Group, String
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.widgetbase import Widget


class EventCalendar(Widget):
    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 300
        self.height = 150
        self.timeColWidth = None  # if declared, use it; otherwise auto-size.
        self.trackRowHeight = 20
        self.data = []  # list of Event objects
        self.trackNames = None

        self.startTime = None  #displays ALL data on day if not set
        self.endTime = None    # displays ALL data on day if not set
        self.day = 0


        # we will keep any internal geometry variables
        # here.  These are computed by computeSize(),
        # which is the first thing done when drawing.
        self._talksVisible = []  # subset of data which will get plotted, cache
        self._startTime = None
        self._endTime = None
        self._trackCount = 0
        self._colWidths = []
        self._colLeftEdges = []  # left edge of each column

    def computeSize(self):
        "Called at start of draw.  Sets various column widths"
        self._talksVisible = self.getRelevantTalks(self.data)
        self._trackCount = len(self.getAllTracks())
        self.computeStartAndEndTimes()
        self._colLeftEdges = [self.x]
        if self.timeColWidth is None:
            w = self.width / (1 + self._trackCount)
            self._colWidths = [w] * (1+ self._trackCount)
            for i in range(self._trackCount):
                self._colLeftEdges.append(self._colLeftEdges[-1] + w)
        else:
            self._colWidths = [self.timeColWidth]
            w = (self.width - self.timeColWidth) / self._trackCount
            for i in range(self._trackCount):
                self._colWidths.append(w)
                self._colLeftEdges.append(self._colLeftEdges[-1] + w)



    def computeStartAndEndTimes(self):
        "Work out first and last times to display"
        if self.startTime:
            self._startTime = self.startTime
        else:
            for (title, speaker, trackId, day, start, duration) in self._talksVisible:

                if self._startTime is None: #first one
                    self._startTime = start
                else:
                    if start < self._startTime:
                        self._startTime = start

        if self.endTime:
            self._endTime = self.endTime
        else:
            for (title, speaker, trackId, day, start, duration) in self._talksVisible:
                if self._endTime is None: #first one
                    self._endTime = start + duration
                else:
                    if start + duration > self._endTime:
                        self._endTime = start + duration




    def getAllTracks(self):
        tracks = []
        for (title, speaker, trackId, day, hours, duration) in self.data:
            if trackId is not None:
                if trackId not in tracks:
                    tracks.append(trackId)
        tracks.sort()
        return tracks

    def getRelevantTalks(self, talkList):
        "Scans for tracks actually used"
        used = []
        for talk in talkList:
            (title, speaker, trackId, day, hours, duration) = talk
            assert trackId != 0, "trackId must be None or 1,2,3... zero not allowed!"
            if day == self.day:
                if (((self.startTime is None) or ((hours + duration) >= self.startTime))
                and ((self.endTime is None) or (hours <= self.endTime))):
                    used.append(talk)
        return used

    def scaleTime(self, theTime):
        "Return y-value corresponding to times given"
        axisHeight = self.height - self.trackRowHeight
        # compute fraction between 0 and 1, 0 is at start of period
        proportionUp = ((theTime - self._startTime) / (self._endTime - self._startTime))
        y = self.y + axisHeight - (axisHeight * proportionUp)
        return y


    def getTalkRect(self, startTime, duration, trackId, text):
        "Return shapes for a specific talk"
        g = Group()
        y_bottom = self.scaleTime(startTime + duration)
        y_top = self.scaleTime(startTime)
        y_height = y_top - y_bottom

        if trackId is None:
            #spans all columns
            x = self._colLeftEdges[1]
            width = self.width - self._colWidths[0]
        else:
            #trackId is 1-based and these arrays have the margin info in column
            #zero, so no need to add 1
            x = self._colLeftEdges[trackId]
            width = self._colWidths[trackId]

        lab = Label()
        lab.setText(text)
        lab.setOrigin(x + 0.5*width, y_bottom+0.5*y_height)
        lab.boxAnchor = 'c'
        lab.width = width
        lab.height = y_height
        lab.fontSize = 6

        r = Rect(x, y_bottom, width, y_height, fillColor=colors.cyan)
        g.add(r)
        g.add(lab)

        #now for a label
        # would expect to color-code and add text
        return g

    def draw(self):
        self.computeSize()
        g = Group()

        # time column
        g.add(Rect(self.x, self.y, self._colWidths[0], self.height - self.trackRowHeight, fillColor=colors.cornsilk))

        # track headers
        x = self.x + self._colWidths[0]
        y = self.y + self.height - self.trackRowHeight
        for trk in range(self._trackCount):
            wid = self._colWidths[trk+1]
            r = Rect(x, y, wid, self.trackRowHeight, fillColor=colors.yellow)
            s = String(x + 0.5*wid, y, 'Track %d' % trk, align='middle')
            g.add(r)
            g.add(s)
            x = x + wid

        for talk in self._talksVisible:
            (title, speaker, trackId, day, start, duration) = talk
            r = self.getTalkRect(start, duration, trackId, title + '\n' + speaker)
            g.add(r)


        return g




def test():
    "Make a conference event for day 1 of UP Python 2003"


    d = Drawing(400,200)

    cal = EventCalendar()
    cal.x = 50
    cal.y = 25
    cal.data = [
        # these might be better as objects instead of tuples, since I
        # predict a large number of "optionsl" variables to affect
        # formatting in future.

        #title, speaker, track id, day, start time (hrs), duration (hrs)
        # track ID is 1-based not zero-based!
        ('Keynote: Why design another programming language?',  'Guido van Rossum', None, 1, 9.0, 1.0),

        ('Siena Web Service Architecture', 'Marc-Andre Lemburg', 1, 1, 10.5, 1.5),
        ('Extreme Programming in Python', 'Chris Withers', 2, 1, 10.5, 1.5),
        ('Pattern Experiences in C++', 'Mark Radford', 3, 1, 10.5, 1.5),
        ('What is the Type of std::toupper()', 'Gabriel Dos Reis', 4, 1, 10.5, 1.5),
        ('Linguistic Variables: Clear Thinking with Fuzzy Logic ', 'Walter Banks', 5, 1, 10.5, 1.5),

        ('lunch, short presentations, vendor presentations', '', None, 1, 12.0, 2.0),

        ("CORBA? Isn't that obsolete", 'Duncan Grisby', 1, 1, 14.0, 1.5),
        ("Python Design Patterns", 'Duncan Booth', 2, 1, 14.0, 1.5),
        ("Inside Security Checks and Safe Exceptions", 'Brandon Bray', 3, 1, 14.0, 1.5),
        ("Studying at a Distance", 'Panel Discussion, Panel to include Alan Lenton & Francis Glassborow', 4, 1, 14.0, 1.5),
        ("Coding Standards - Given the ANSI C Standard why do I still need a coding Standard", 'Randy Marques', 5, 1, 14.0, 1.5),

        ("RESTful Python", 'Hamish Lawson', 1, 1, 16.0, 1.5),
        ("Parsing made easier - a radical old idea", 'Andrew Koenig', 2, 1, 16.0, 1.5),
        ("C++ & Multimethods", 'Julian Smith', 3, 1, 16.0, 1.5),
        ("C++ Threading", 'Kevlin Henney', 4, 1, 16.0, 1.5),
        ("The Organisation Strikes Back", 'Alan Griffiths & Sarah Lees', 5, 1, 16.0, 1.5),

        ('Birds of a Feather meeting', '', None, 1, 17.5, 2.0),

        ('Keynote: In the Spirit of C',  'Greg Colvin', None, 2, 9.0, 1.0),

        ('The Infinite Filing Cabinet - object storage in Python', 'Jacob Hallen', 1, 2, 10.5, 1.5),
        ('Introduction to Python and Jython for C++ and Java Programmers', 'Alex Martelli', 2, 2, 10.5, 1.5),
        ('Template metaprogramming in Haskell', 'Simon Peyton Jones', 3, 2, 10.5, 1.5),
        ('Plenty People Programming: C++ Programming in a Group, Workshop with a difference', 'Nico Josuttis', 4, 2, 10.5, 1.5),
        ('Design and Implementation of the Boost Graph Library', 'Jeremy Siek', 5, 2, 10.5, 1.5),

        ('lunch, short presentations, vendor presentations', '', None, 2, 12.0, 2.0),

        ("Building GUI Applications with PythonCard and PyCrust", 'Andy Todd', 1, 2, 14.0, 1.5),
        ("Integrating Python, C and C++", 'Duncan Booth', 2, 2, 14.0, 1.5),
        ("Secrets and Pitfalls of Templates", 'Nicolai Josuttis & David Vandevoorde', 3, 2, 14.0, 1.5),
        ("Being a Mentor", 'Panel Discussion, Panel to include Alan Lenton & Francis Glassborow', 4, 2, 14.0, 1.5),
        ("The Embedded C Extensions to C", 'Willem Wakker', 5, 2, 14.0, 1.5),

        ("Lightning Talks", 'Paul Brian', 1, 2, 16.0, 1.5),
        ("Scripting Java Applications with Jython", 'Anthony Eden', 2, 2, 16.0, 1.5),
        ("Metaprogramming and the Boost Metaprogramming Library", 'David Abrahams', 3, 2, 16.0, 1.5),
        ("A Common Vendor ABI for C++ -- GCC's why, what and not", 'Nathan Sidwell & Gabriel Dos Reis', 4, 2, 16.0, 1.5),
        ("The Timing and Cost of Choices", 'Hubert Matthews', 5, 2, 16.0, 1.5),

        ('Birds of a Feather meeting', '', None, 2, 17.5, 2.0),

        ('Keynote: The Cost of C &amp; C++ Compatibility', 'Andy Koenig', None, 3, 9.0, 1.0),

        ('Prying Eyes: Generic Observer Implementations in C++', 'Andrei Alexandrescu', 1, 2, 10.5, 1.5),
        ('The Roadmap to Generative Programming With C++', 'Ulrich Eisenecker', 2, 2, 10.5, 1.5),
        ('Design Patterns in C++ and C# for the Common Language Runtime', 'Brandon Bray', 3, 2, 10.5, 1.5),
        ('Extreme Hour (XH): (workshop) - Jutta Eckstein and Nico Josuttis', 'Jutta Ecstein', 4, 2, 10.5, 1.5),
        ('The Lambda Library : Unnamed Functions for C++', 'Jaako Jarvi', 5, 2, 10.5, 1.5),

        ('lunch, short presentations, vendor presentations', '', None, 3, 12.0, 2.0),

        ('Reflective Metaprogramming', 'Daveed Vandevoorde', 1, 3, 14.0, 1.5),
        ('Advanced Template Issues and Solutions (double session)', 'Herb Sutter',2, 3, 14.0, 3),
        ('Concurrent Programming in Java (double session)', 'Angelika Langer', 3, 3, 14.0, 3),
        ('What can MISRA-C (2nd Edition) do for us?', 'Chris Hills', 4, 3, 14.0, 1.5),
        ('C++ Metaprogramming Concepts and Results', 'Walter E Brown', 5, 3, 14.0, 1.5),

        ('Binding C++ to Python with the Boost Python Library', 'David Abrahams', 1, 3, 16.0, 1.5),
        ('Using Aspect Oriented Programming for Enterprise Application Integration', 'Arno Schmidmeier', 4, 3, 16.0, 1.5),
        ('Defective C++', 'Marc Paterno', 5, 3, 16.0, 1.5),

        ("Speakers' Banquet & Birds of a Feather meeting", '', None, 3, 17.5, 2.0),

        ('Keynote: The Internet, Software and Computers - A Report Card', 'Alan Lenton',  None, 4, 9.0, 1.0),

        ('Multi-Platform Software Development; Lessons from the Boost libraries', 'Beman Dawes', 1, 5, 10.5, 1.5),
        ('The Stability of the C++ ABI', 'Steve Clamage', 2, 5, 10.5, 1.5),
        ('Generic Build Support - A Pragmatic Approach to the Software Build Process', 'Randy Marques', 3, 5, 10.5, 1.5),
        ('How to Handle Project Managers: a survival guide', 'Barb Byro',  4, 5, 10.5, 1.5),

        ('lunch, ACCU AGM', '', None, 5, 12.0, 2.0),

        ('Sauce: An OO recursive descent parser; its design and implementation.', 'Jon Jagger', 1, 5, 14.0, 1.5),
        ('GNIRTS ESAC REWOL -  Bringing the UNIX filters to the C++ iostream library.', 'JC van Winkel', 2, 5, 14.0, 1.5),
        ('Pattern Writing: Live and Direct', 'Frank Buschmann & Kevlin Henney',  3, 5, 14.0, 3.0),
        ('The Future of Programming Languages - A Goldfish Bowl', 'Francis Glassborow and friends',  3, 5, 14.0, 1.5),

        ('Honey, I Shrunk the Threads: Compile-time checked multithreaded transactions in C++', 'Andrei Alexandrescu', 1, 5, 16.0, 1.5),
        ('Fun and Functionality with Functors', 'Lois Goldthwaite', 2, 5, 16.0, 1.5),
        ('Agile Enough?', 'Alan Griffiths', 4, 5, 16.0, 1.5),
        ("Conference Closure: A brief plenary session", '', None, 5, 17.5, 0.5),

        ]

    #return cal
    cal.day = 1

    d.add(cal)


    for format in ['pdf']:#,'gif','png']:
        out = d.asString(format)
        open('eventcal.%s' % format, 'wb').write(out)
        print('saved eventcal.%s' % format)

if __name__=='__main__':
    test()
