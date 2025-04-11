"""
ldapurl - handling of LDAP URLs as described in RFC 4516

See https://www.python-ldap.org/ for details.
"""

__version__ = '3.4.0'

__all__ = [
  # constants
  'SEARCH_SCOPE','SEARCH_SCOPE_STR',
  'LDAP_SCOPE_BASE','LDAP_SCOPE_ONELEVEL','LDAP_SCOPE_SUBTREE',
  # functions
  'isLDAPUrl',
  # classes
  'LDAPUrlExtension','LDAPUrlExtensions','LDAPUrl'
]

from collections.abc import MutableMapping
from urllib.parse import quote, unquote

LDAP_SCOPE_BASE = 0
LDAP_SCOPE_ONELEVEL = 1
LDAP_SCOPE_SUBTREE = 2
LDAP_SCOPE_SUBORDINATES = 3

SEARCH_SCOPE_STR = {
  None:'',
  LDAP_SCOPE_BASE:'base',
  LDAP_SCOPE_ONELEVEL:'one',
  LDAP_SCOPE_SUBTREE:'sub',
  LDAP_SCOPE_SUBORDINATES:'subordinates',
}

SEARCH_SCOPE = {
  '':None,
  # the search scope strings defined in RFC 4516
  'base':LDAP_SCOPE_BASE,
  'one':LDAP_SCOPE_ONELEVEL,
  'sub':LDAP_SCOPE_SUBTREE,
  # from draft-sermersheim-ldap-subordinate-scope
  'subordinates':LDAP_SCOPE_SUBORDINATES,
}

# Some widely used types
StringType = type('')
TupleType=type(())


def isLDAPUrl(s):
  """Returns True if s is a LDAP URL, else False
  """
  return s.lower().startswith(('ldap://', 'ldaps://', 'ldapi://'))


def ldapUrlEscape(s):
  """Returns URL encoding of string s"""
  return quote(s).replace(',','%2C').replace('/','%2F')

class LDAPUrlExtension:
  """
  Class for parsing and unparsing LDAP URL extensions
  as described in RFC 4516.

  Usable class attributes:
    critical
          Boolean integer marking the extension as critical
    extype
          Type of extension
    exvalue
          Value of extension
  """

  def __init__(self,extensionStr=None,critical=0,extype=None,exvalue=None):
    self.critical = critical
    self.extype = extype
    self.exvalue = exvalue
    if extensionStr:
      self._parse(extensionStr)

  def _parse(self,extension):
    extension = extension.strip()
    if not extension:
      # Don't parse empty strings
      self.extype,self.exvalue = None,None
      return
    self.critical = extension[0]=='!'
    if extension[0]=='!':
      extension = extension[1:].strip()
    try:
      self.extype,self.exvalue = extension.split('=',1)
    except ValueError:
      # No value, just the extype
      self.extype,self.exvalue = extension,None
    else:
      self.exvalue = unquote(self.exvalue.strip())
    self.extype = self.extype.strip()

  def unparse(self):
    if self.exvalue is None:
      return '{}{}'.format('!'*(self.critical>0),self.extype)
    else:
      return '{}{}={}'.format(
        '!'*(self.critical>0),
        self.extype,quote(self.exvalue or '')
      )

  def __str__(self):
    return self.unparse()

  def __repr__(self):
    return '<{}.{} instance at {}: {}>'.format(
      self.__class__.__module__,
      self.__class__.__name__,
      hex(id(self)),
      self.__dict__
    )

  def __eq__(self,other):
    return \
      (self.critical==other.critical) and \
      (self.extype==other.extype) and \
      (self.exvalue==other.exvalue)

  def __ne__(self,other):
    return not self.__eq__(other)


class LDAPUrlExtensions(MutableMapping):
    """
    Models a collection of LDAP URL extensions as
    a mapping type
    """
    __slots__ = ('_data', )

    def __init__(self, default=None):
        self._data = {}
        if default is not None:
            self.update(default)

    def __setitem__(self, name, value):
        """Store an extension

        name
            string
        value
            LDAPUrlExtension instance, whose extype nust match `name`
        """
        if not isinstance(value, LDAPUrlExtension):
            raise TypeError("value must be LDAPUrlExtension, not "
                            + type(value).__name__)
        if name != value.extype:
            raise ValueError(
                "key {!r} does not match extension type {!r}".format(
                    name, value.extype))
        self._data[name] = value

    def __getitem__(self, name):
        return self._data[name]

    def __delitem__(self, name):
        del self._data[name]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __str__(self):
        return ','.join(str(v) for v in self.values())

    def __repr__(self):
        return '<{}.{} instance at {}: {}>'.format(
            self.__class__.__module__,
            self.__class__.__name__,
            hex(id(self)),
            self._data
        )

    def __eq__(self,other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._data == other._data

    def parse(self,extListStr):
        for extension_str in extListStr.strip().split(','):
            if extension_str:
                e = LDAPUrlExtension(extension_str)
                self[e.extype] = e

    def unparse(self):
        return ','.join(v.unparse() for v in self.values())


class LDAPUrl:
  """
  Class for parsing and unparsing LDAP URLs
  as described in RFC 4516.

  Usable class attributes:
    urlscheme
        URL scheme (either ldap, ldaps or ldapi)
    hostport
        LDAP host (default '')
    dn
        String holding distinguished name (default '')
    attrs
        list of attribute types (default None)
    scope
        integer search scope for ldap-module
    filterstr
        String representation of LDAP Search Filters
        (see RFC 4515)
    extensions
        Dictionary used as extensions store
    who
        Maps automagically to bindname LDAP URL extension
    cred
        Maps automagically to X-BINDPW LDAP URL extension
  """

  attr2extype = {'who':'bindname','cred':'X-BINDPW'}

  def __init__(
    self,
    ldapUrl=None,
    urlscheme='ldap',
    hostport='',dn='',attrs=None,scope=None,filterstr=None,
    extensions=None,
    who=None,cred=None
  ):
    self.urlscheme=urlscheme.lower()
    self.hostport=hostport
    self.dn=dn
    self.attrs=attrs
    self.scope=scope
    self.filterstr=filterstr
    self.extensions=(extensions or LDAPUrlExtensions({}))
    if ldapUrl!=None:
      self._parse(ldapUrl)
    if who!=None:
      self.who = who
    if cred!=None:
      self.cred = cred

  def __eq__(self,other):
    return \
      self.urlscheme==other.urlscheme and \
      self.hostport==other.hostport and \
      self.dn==other.dn and \
      self.attrs==other.attrs and \
      self.scope==other.scope and \
      self.filterstr==other.filterstr and \
      self.extensions==other.extensions

  def __ne__(self,other):
    return not self.__eq__(other)

  def _parse(self,ldap_url):
    """
    parse a LDAP URL and set the class attributes
    urlscheme,host,dn,attrs,scope,filterstr,extensions
    """
    if not isLDAPUrl(ldap_url):
      raise ValueError('Value %s for ldap_url does not seem to be a LDAP URL.' % (repr(ldap_url)))
    scheme,rest = ldap_url.split('://',1)
    self.urlscheme = scheme.lower()
    slash_pos = rest.find('/')
    qemark_pos = rest.find('?')
    if (slash_pos==-1) and (qemark_pos==-1):
      # No / and ? found at all
      self.hostport = unquote(rest)
      self.dn = ''
      return
    else:
      if slash_pos!=-1 and (qemark_pos==-1 or (slash_pos<qemark_pos)):
        # Slash separates DN from hostport
        self.hostport = unquote(rest[:slash_pos])
        # Eat the slash from rest
        rest = rest[slash_pos+1:]
      elif qemark_pos!=1 and (slash_pos==-1 or (slash_pos>qemark_pos)):
        # Question mark separates hostport from rest, DN is assumed to be empty
        self.hostport = unquote(rest[:qemark_pos])
        # Do not eat question mark
        rest = rest[qemark_pos:]
      else:
        raise ValueError('Something completely weird happened!')
    paramlist=rest.split('?',4)
    paramlist_len = len(paramlist)
    if paramlist_len>=1:
      self.dn = unquote(paramlist[0]).strip()
    if (paramlist_len>=2) and (paramlist[1]):
      self.attrs = unquote(paramlist[1].strip()).split(',')
    if paramlist_len>=3:
      scope = paramlist[2].strip()
      try:
        self.scope = SEARCH_SCOPE[scope]
      except KeyError:
        raise ValueError('Invalid search scope %s' % (repr(scope)))
    if paramlist_len>=4:
      filterstr = paramlist[3].strip()
      if not filterstr:
        self.filterstr = None
      else:
        self.filterstr = unquote(filterstr)
    if paramlist_len>=5:
      if paramlist[4]:
        self.extensions = LDAPUrlExtensions()
        self.extensions.parse(paramlist[4])
      else:
        self.extensions = None
    return

  def applyDefaults(self,defaults):
    """
    Apply defaults to all class attributes which are None.

    defaults
        Dictionary containing a mapping from class attributes
        to default values
    """
    for k, value in defaults.items():
      if getattr(self,k) is None:
        setattr(self, k, value)

  def initializeUrl(self):
    """
    Returns LDAP URL suitable to be passed to ldap.initialize()
    """
    if self.urlscheme=='ldapi':
      # hostport part might contain slashes when ldapi:// is used
      hostport = ldapUrlEscape(self.hostport)
    else:
      hostport = self.hostport
    return f'{self.urlscheme}://{hostport}'

  def unparse(self):
    """
    Returns LDAP URL depending on class attributes set.
    """
    if self.attrs is None:
      attrs_str = ''
    else:
      attrs_str = ','.join(self.attrs)
    scope_str = SEARCH_SCOPE_STR[self.scope]
    if self.filterstr is None:
      filterstr = ''
    else:
      filterstr = ldapUrlEscape(self.filterstr)
    dn = ldapUrlEscape(self.dn)
    if self.urlscheme=='ldapi':
      # hostport part might contain slashes when ldapi:// is used
      hostport = ldapUrlEscape(self.hostport)
    else:
      hostport = self.hostport
    ldap_url = '{}://{}/{}?{}?{}?{}'.format(
      self.urlscheme,
      hostport,dn,attrs_str,scope_str,filterstr
    )
    if self.extensions:
      ldap_url = ldap_url+'?'+self.extensions.unparse()
    return ldap_url

  def htmlHREF(self,urlPrefix='',hrefText=None,hrefTarget=None):
    """
    Returns a string with HTML link for this LDAP URL.

    urlPrefix
        Prefix before LDAP URL (e.g. for addressing another web-based client)
    hrefText
        link text/description
    hrefTarget
        string added as link target attribute
    """
    if not isinstance(urlPrefix, str):
        raise TypeError("urlPrefix must be str, not "
                        + type(urlPrefix).__name__)
    if hrefText is None:
        hrefText = self.unparse()
    if not isinstance(hrefText, str):
        raise TypeError("hrefText must be str, not "
                        + type(hrefText).__name__)
    if hrefTarget is None:
        target = ''
    else:
        if not isinstance(hrefTarget, str):
            raise TypeError("hrefTarget must be str, not "
                            + type(hrefTarget).__name__)
        target = ' target="%s"' % hrefTarget
    return '<a{} href="{}{}">{}</a>'.format(
        target, urlPrefix, self.unparse(), hrefText
    )

  def __str__(self):
    return self.unparse()

  def __repr__(self):
    return '<{}.{} instance at {}: {}>'.format(
      self.__class__.__module__,
      self.__class__.__name__,
      hex(id(self)),
      self.__dict__
    )

  def __getattr__(self,name):
    if name in self.attr2extype:
      extype = self.attr2extype[name]
      if self.extensions and \
         extype in self.extensions and \
         not self.extensions[extype].exvalue is None:
        result = unquote(self.extensions[extype].exvalue)
      else:
        return None
    else:
      raise AttributeError('{} has no attribute {}'.format(
        self.__class__.__name__,name
      ))
    return result # __getattr__()

  def __setattr__(self,name,value):
    if name in self.attr2extype:
      extype = self.attr2extype[name]
      if value is None:
        # A value of None means that extension is deleted
        delattr(self,name)
      elif value!=None:
        # Add appropriate extension
        self.extensions[extype] = LDAPUrlExtension(
          extype=extype,exvalue=unquote(value)
        )
    else:
      self.__dict__[name] = value

  def __delattr__(self,name):
    if name in self.attr2extype:
      extype = self.attr2extype[name]
      if self.extensions:
        try:
          del self.extensions[extype]
        except KeyError:
          pass
    else:
      del self.__dict__[name]
