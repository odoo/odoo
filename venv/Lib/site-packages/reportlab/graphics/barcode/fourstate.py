#
# Copyright (c) 2000 Tyler C. Sarna <tsarna@sarna.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. All advertising materials mentioning features or use of this software
#    must display the following acknowledgement:
#      This product includes software developed by Tyler C. Sarna.
# 4. Neither the name of the author nor the names of contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

# . 3 T Tracker
# , 2 D Descender
# ' 1 A Ascender
# | 0 H Ascender/Descender

_rm_patterns = {
    "0" : "--||",   "1" : "-',|",   "2" : "-'|,",   "3" : "'-,|",
    "4" : "'-|,",   "5" : "'',,",   "6" : "-,'|",   "7" : "-|-|",
    "8" : "-|',",   "9" : "',-|",   "A" : "',',",   "B" : "'|-,",
    "C" : "-,|'",   "D" : "-|,'",   "E" : "-||-",   "F" : "',,'",
    "G" : "',|-",   "H" : "'|,-",   "I" : ",-'|",   "J" : ",'-|",
    "K" : ",'',",   "L" : "|--|",   "M" : "|-',",   "N" : "|'-,",
    "O" : ",-|'",   "P" : ",','",   "Q" : ",'|-",   "R" : "|-,'",
    "S" : "|-|-",   "T" : "|',-",   "U" : ",,''",   "V" : ",|-'",
    "W" : ",|'-",   "X" : "|,-'",   "Y" : "|,'-",   "Z" : "||--",

    # start, stop
    "(" : "'-,'",   ")" : "'|,|"
}

_ozN_patterns = {
    "0" : "||",    "1" : "|'",    "2" : "|,",    "3" : "'|",    "4" : "''",
    "5" : "',",    "6" : ",|",    "7" : ",'",    "8" : ",,",    "9" : ".|"
}

_ozC_patterns = {
    "A" : "|||",    "B" : "||'",    "C" : "||,",    "D" : "|'|",
    "E" : "|''",    "F" : "|',",    "G" : "|,|",    "H" : "|,'",
    "I" : "|,,",    "J" : "'||",    "K" : "'|'",    "L" : "'|,",
    "M" : "''|",    "N" : "'''",    "O" : "'',",    "P" : "',|",
    "Q" : "','",    "R" : "',,",    "S" : ",||",    "T" : ",|'",
    "U" : ",|,",    "V" : ",'|",    "W" : ",''",    "X" : ",',",
    "Y" : ",,|",    "Z" : ",,'",    "a" : "|,.",    "b" : "|.|",
    "c" : "|.'",    "d" : "|.,",    "e" : "|..",    "f" : "'|.",
    "g" : "''.",    "h" : "',.",    "i" : "'.|",    "j" : "'.'",
    "k" : "'.,",    "l" : "'..",    "m" : ",|.",    "n" : ",'.",
    "o" : ",,.",    "p" : ",.|",    "q" : ",.'",    "r" : ",.,",
    "s" : ",..",    "t" : ".|.",    "u" : ".'.",    "v" : ".,.",
    "w" : "..|",    "x" : "..'",    "y" : "..,",    "z" : "...",
    "0" : ",,,",    "1" : ".||",    "2" : ".|'",    "3" : ".|,",
    "4" : ".'|",    "5" : ".''",    "6" : ".',",    "7" : ".,|",
    "8" : ".,'",    "9" : ".,,",    " " : "||.",    "#" : "|'.",
}

#http://www.auspost.com.au/futurepost/
