import sys
sys.stderr = sys.stdout

from TransitionMaps import TransitionMap

m = TransitionMap()
print m

def add(c, s):
  print
  print "adding", repr(c), "-->", repr(s)
  m.add_transition(c, s)
  print m
  print "keys:", m.keys()

add('a','alpha')
add('e', 'eta')
add('f', 'foo')
add('i', 'iota')
add('i', 'imp')
add('eol', 'elephant')



