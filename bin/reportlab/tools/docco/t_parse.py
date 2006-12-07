#Copyright ReportLab Europe Ltd. 2000-2004
#see license.txt for license details
#history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/tools/docco/t_parse.py
"""
Template parsing module inspired by REXX (with thanks to Donn Cave for discussion).

Template initialization has the form:
   T = Template(template_string, wild_card_marker, single_char_marker,
             x = regex_x, y = regex_y, ...)
Parsing has the form
   ([match1, match2, ..., matchn], lastindex) = T.PARSE(string)

Only the first argument is mandatory.

The resultant object efficiently parses strings that match the template_string,
giving a list of substrings that correspond to each "directive" of the template.

Template directives:

  Wildcard:
    The template may be initialized with a wildcard that matches any string
    up to the string matching the next directive (which may not be a wild
    card or single character marker) or the next literal sequence of characters
    of the template.  The character that represents a wildcard is specified
    by the wild_card_marker parameter, which has no default.

    For example, using X as the wildcard:


    >>> T = Template("prefixXinteriorX", "X")
    >>> T.PARSE("prefix this is before interior and this is after")
    ([' this is before ', ' and this is after'], 47)
    >>> T = Template("<X>X<X>", "X")
    >>> T.PARSE('<A HREF="index.html">go to index</A>')
    (['A HREF="index.html"', 'go to index', '/A'], 36)

    Obviously the character used to represent the wildcard must be distinct
    from the characters used to represent literals or other directives.

  Fixed length character sequences:
    The template may have a marker character which indicates a fixed
    length field.  All adjacent instances of this marker will be matched
    by a substring of the same length in the parsed string.  For example:

      >>> T = Template("NNN-NN-NNNN", single_char_marker="N")
      >>> T.PARSE("1-2-34-5-12")
      (['1-2', '34', '5-12'], 11)
      >>> T.PARSE("111-22-3333")
      (['111', '22', '3333'], 11)
      >>> T.PARSE("1111-22-3333")
      ValueError: literal not found at (3, '-')

    A template may have multiple fixed length markers, which allows fixed
    length fields to be adjacent, but recognized separately.  For example:

      >>> T = Template("MMDDYYX", "X", "MDY")
      >>> T.PARSE("112489 Somebody's birthday!")
      (['11', '24', '89', " Somebody's birthday!"], 27)

  Regular expression markers:
    The template may have markers associated with regular expressions.
    the regular expressions may be either string represenations of compiled.
    For example:
      >>> T = Template("v: s i", v=id, s=str, i=int)
      >>> T.PARSE("this_is_an_identifier: 'a string' 12344")
      (['this_is_an_identifier', "'a string'", '12344'], 39)
      >>>
    Here id, str, and int are regular expression conveniences provided by
    this module.

  Directive markers may be mixed and matched, except that wildcards cannot precede
  wildcards or single character markers.
  Example:
>>> T = Template("ssnum: NNN-NN-NNNN, fn=X, ln=X, age=I, quote=Q", "X", "N", I=int, Q=str)
>>> T.PARSE("ssnum: 123-45-6789, fn=Aaron, ln=Watters, age=13, quote='do be do be do'")
(['123', '45', '6789', 'Aaron', 'Watters', '13', "'do be do be do'"], 72)
>>>

"""

import re, string
from types import StringType
from string import find

#
# template parsing
#
# EG: T = Template("(NNN)NNN-NNNN X X", "X", "N")
#     ([area, exch, ext, fn, ln], index) = T.PARSE("(908)949-2726 Aaron Watters")
#
class Template:

   def __init__(self,
                template,
                wild_card_marker=None,
                single_char_marker=None,
                **marker_to_regex_dict):
       self.template = template
       self.wild_card = wild_card_marker
       self.char = single_char_marker
       # determine the set of markers for this template
       markers = marker_to_regex_dict.keys()
       if wild_card_marker:
          markers.append(wild_card_marker)
       if single_char_marker:
          for ch in single_char_marker: # allow multiple scm's
              markers.append(ch)
          self.char = single_char_primary = single_char_marker[0]
       self.markers = markers
       for mark in markers:
           if len(mark)>1:
              raise ValueError, "Marks must be single characters: "+`mark`
       # compile the regular expressions if needed
       self.marker_dict = marker_dict = {}
       for (mark, rgex) in marker_to_regex_dict.items():
           if type(rgex) == StringType:
              rgex = re.compile(rgex)
           marker_dict[mark] = rgex
       # determine the parse sequence
       parse_seq = []
       # dummy last char
       lastchar = None
       index = 0
       last = len(template)
       # count the number of directives encountered
       ndirectives = 0
       while index<last:
          start = index
          thischar = template[index]
          # is it a wildcard?
          if thischar == wild_card_marker:
             if lastchar == wild_card_marker:
                raise ValueError, "two wild cards in sequence is not allowed"
             parse_seq.append( (wild_card_marker, None) )
             index = index+1
             ndirectives = ndirectives+1
          # is it a sequence of single character markers?
          elif single_char_marker and thischar in single_char_marker:
             if lastchar == wild_card_marker:
                raise ValueError, "wild card cannot precede single char marker"
             while index<last and template[index] == thischar:
                index = index+1
             parse_seq.append( (single_char_primary, index-start) )
             ndirectives = ndirectives+1
          # is it a literal sequence?
          elif not thischar in markers:
             while index<last and not template[index] in markers:
                index = index+1
             parse_seq.append( (None, template[start:index]) )
          # otherwise it must be a re marker
          else:
             rgex = marker_dict[thischar]
             parse_seq.append( (thischar, rgex) )
             ndirectives = ndirectives+1
             index = index+1
          lastchar = template[index-1]
       self.parse_seq = parse_seq
       self.ndirectives = ndirectives

   def PARSE(self, str, start=0):
       ndirectives = self.ndirectives
       wild_card = self.wild_card
       single_char = self.char
       parse_seq = self.parse_seq
       lparse_seq = len(parse_seq) - 1
       # make a list long enough for substitutions for directives
       result = [None] * ndirectives
       current_directive_index = 0
       currentindex = start
       # scan through the parse sequence, recognizing
       for parse_index in xrange(lparse_seq + 1):
           (indicator, data) = parse_seq[parse_index]
           # is it a literal indicator?
           if indicator is None:
              if find(str, data, currentindex) != currentindex:
                 raise ValueError, "literal not found at "+`(currentindex,data)`
              currentindex = currentindex + len(data)
           else:
              # anything else is a directive
              # is it a wildcard?
              if indicator == wild_card:
                 # if it is the last directive then it matches the rest of the string
                 if parse_index == lparse_seq:
                    last = len(str)
                 # otherwise must look at next directive to find end of wildcard
                 else:
                    # next directive must be re or literal
                    (nextindicator, nextdata) = parse_seq[parse_index+1]
                    if nextindicator is None:
                       # search for literal
                       last = find(str, nextdata, currentindex)
                       if last<currentindex:
                          raise ValueError, \
                           "couldn't terminate wild with lit "+`currentindex`
                    else:
                       # data is a re, search for it
                       last = nextdata.search(str, currentindex)
                       if last<currentindex:
                          raise ValueError, \
                           "couldn't terminate wild with re "+`currentindex`
              elif indicator == single_char:
                 # data is length to eat
                 last = currentindex + data
              else:
                 # other directives are always regular expressions
                 last = data.match(str, currentindex) + currentindex
                 if last<currentindex:
                    raise ValueError, "couldn't match re at "+`currentindex`
              #print "accepting", str[currentindex:last]
              result[current_directive_index] = str[currentindex:last]
              current_directive_index = current_directive_index+1
              currentindex = last
       # sanity check
       if current_directive_index != ndirectives:
          raise SystemError, "not enough directives found?"
       return (result, currentindex)

# some useful regular expressions
USERNAMEREGEX = \
  "["+string.letters+"]["+string.letters+string.digits+"_]*"
STRINGLITREGEX = "'[^\n']*'"
SIMPLEINTREGEX = "["+string.digits+"]+"
id = re.compile(USERNAMEREGEX)
str = re.compile(STRINGLITREGEX)
int = re.compile(SIMPLEINTREGEX)

def test():
    global T, T1, T2, T3

    T = Template("(NNN)NNN-NNNN X X", "X", "N")
    print T.PARSE("(908)949-2726 Aaron Watters")

    T1 = Template("s --> s blah", s=str)
    s = "' <-- a string --> ' --> 'blah blah another string blah' blah"
    print T1.PARSE(s)

    T2 = Template("s --> NNNiX", "X", "N", s=str, i=int)
    print T2.PARSE("'A STRING' --> 15964653alpha beta gamma")

    T3 = Template("XsXi", "X", "N", s=str, i=int)
    print T3.PARSE("prefix'string'interior1234junk not parsed")

    T4 = Template("MMDDYYX", "X", "MDY")
    print T4.PARSE("122961 Somebody's birthday!")


if __name__=="__main__": test()