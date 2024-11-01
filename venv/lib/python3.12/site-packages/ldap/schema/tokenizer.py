"""
ldap.schema.tokenizer - Low-level parsing functions for schema element strings

See https://www.python-ldap.org/ for details.
"""

import re

TOKENS_FINDALL = re.compile(
    r"(\()"           # opening parenthesis
    r"|"              # or
    r"(\))"           # closing parenthesis
    r"|"              # or
    r"([^'$()\s]+)"   # string of length >= 1 without '$() or whitespace
    r"|"              # or
    r"('(?:[^'\\]|\\.)*'(?!\w))"
                      # any string or empty string surrounded by unescaped
                      # single quotes except if right quote is succeeded by
                      # alphanumeric char
    r"|"              # or
    r"([^\s]+?)",     # residue, all non-whitespace strings
).findall

UNESCAPE_PATTERN = re.compile(r"\\(.)")


def split_tokens(s):
    """
    Returns list of syntax elements with quotes and spaces stripped.
    """
    parts = []
    parens = 0
    for opar, cpar, unquoted, quoted, residue in TOKENS_FINDALL(s):
        if unquoted:
            parts.append(unquoted)
        elif quoted:
            parts.append(UNESCAPE_PATTERN.sub(r'\1', quoted[1:-1]))
        elif opar:
            parens += 1
            parts.append(opar)
        elif cpar:
            parens -= 1
            parts.append(cpar)
        elif residue == '$':
            if not parens:
                raise ValueError("'$' outside parenthesis in %r" % (s))
        else:
            raise ValueError(residue, s)
    if parens:
        raise ValueError("Unbalanced parenthesis in %r" % (s))
    return parts

def extract_tokens(l,known_tokens):
  """
  Returns dictionary of known tokens with all values
  """
  assert l[0].strip()=="(" and l[-1].strip()==")",ValueError(l)
  result = {}
  result.update(known_tokens)
  i = 0
  l_len = len(l)
  while i<l_len:
    if l[i] in result:
      token = l[i]
      i += 1 # Consume token
      if i<l_len:
        if l[i] in result:
          # non-valued
          result[token] = (())
        elif l[i]=="(":
          # multi-valued
          i += 1 # Consume left parentheses
          start = i
          while i<l_len and l[i]!=")":
            i += 1
          result[token] = tuple(filter(lambda v:v!='$',l[start:i]))
          i += 1 # Consume right parentheses
        else:
          # single-valued
          result[token] = l[i],
          i += 1 # Consume single value
    else:
      i += 1 # Consume unrecognized item
  return result
