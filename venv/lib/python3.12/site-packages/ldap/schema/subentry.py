"""
ldap.schema.subentry -  subschema subentry handling

See https://www.python-ldap.org/ for details.
"""

import copy
from urllib.request import urlopen

import ldap.cidict,ldap.schema
from ldap.schema.models import *

import ldapurl
import ldif


SCHEMA_CLASS_MAPPING = ldap.cidict.cidict()
SCHEMA_ATTR_MAPPING = {}

for o in list(vars().values()):
  if hasattr(o,'schema_attribute'):
    SCHEMA_CLASS_MAPPING[o.schema_attribute] = o
    SCHEMA_ATTR_MAPPING[o] = o.schema_attribute

SCHEMA_ATTRS = list(SCHEMA_CLASS_MAPPING)


class SubschemaError(ValueError):
  pass


class OIDNotUnique(SubschemaError):

  def __init__(self,desc):
    self.desc = desc

  def __str__(self):
    return 'OID not unique for %s' % (self.desc)


class NameNotUnique(SubschemaError):

  def __init__(self,desc):
    self.desc = desc

  def __str__(self):
    return 'NAME not unique for %s' % (self.desc)


class SubSchema:
  """
  Arguments:

  sub_schema_sub_entry
      Dictionary usually returned by LDAP search or the LDIF parser
      containing the sub schema sub entry

  check_uniqueness
      Defines whether uniqueness of OIDs and NAME is checked.

      0
        no check
      1
        check but add schema description with work-around
      2
        check and raise exception if non-unique OID or NAME is found

  Class attributes:

  sed
    Dictionary holding the subschema information as pre-parsed
    SchemaElement objects (do not access directly!)
  name2oid
    Dictionary holding the mapping from NAMEs to OIDs
    (do not access directly!)
  non_unique_oids
    List of OIDs used at least twice in the subschema
  non_unique_names
    List of NAMEs used at least twice in the subschema for the same schema element
  """

  def __init__(self,sub_schema_sub_entry,check_uniqueness=1):

    # Initialize all dictionaries
    self.name2oid = {}
    self.sed = {}
    self.non_unique_oids = {}
    self.non_unique_names = {}
    for c in SCHEMA_CLASS_MAPPING.values():
      self.name2oid[c] = ldap.cidict.cidict()
      self.sed[c] = {}
      self.non_unique_names[c] = ldap.cidict.cidict()

    # Transform entry dict to case-insensitive dict
    e = ldap.cidict.cidict(sub_schema_sub_entry)

    # Build the schema registry in dictionaries
    for attr_type in SCHEMA_ATTRS:

      for attr_value in filter(None,e.get(attr_type,[])):

        se_class = SCHEMA_CLASS_MAPPING[attr_type]
        se_instance = se_class(attr_value)
        se_id = se_instance.get_id()

        if check_uniqueness and se_id in self.sed[se_class]:
            self.non_unique_oids[se_id] = None
            if check_uniqueness==1:
              # Add to subschema by adding suffix to ID
              suffix_counter = 1
              new_se_id = se_id
              while new_se_id in self.sed[se_class]:
                new_se_id = ';'.join((se_id,str(suffix_counter)))
                suffix_counter += 1
              else:
                se_id = new_se_id
            elif check_uniqueness>=2:
              raise OIDNotUnique(attr_value)

        # Store the schema element instance in the central registry
        self.sed[se_class][se_id] = se_instance

        if hasattr(se_instance,'names'):
          for name in ldap.cidict.cidict({}.fromkeys(se_instance.names)):
            if check_uniqueness and name in self.name2oid[se_class]:
              self.non_unique_names[se_class][se_id] = None
              raise NameNotUnique(attr_value)
            else:
              self.name2oid[se_class][name] = se_id

    # Turn dict into list maybe more handy for applications
    self.non_unique_oids = list(self.non_unique_oids)

    return # subSchema.__init__()


  def ldap_entry(self):
    """
    Returns a dictionary containing the sub schema sub entry
    """
    # Initialize the dictionary with empty lists
    entry = {}
    # Collect the schema elements and store them in
    # entry's attributes
    for se_class, elements in self.sed.items():
      for se in elements.values():
        se_str = str(se)
        try:
          entry[SCHEMA_ATTR_MAPPING[se_class]].append(se_str)
        except KeyError:
          entry[SCHEMA_ATTR_MAPPING[se_class]] = [ se_str ]
    return entry

  def listall(self,schema_element_class,schema_element_filters=None):
    """
    Returns a list of OIDs of all available schema
    elements of a given schema element class.
    """
    avail_se = self.sed[schema_element_class]
    if schema_element_filters:
      result = []
      for se_key, se in avail_se.items():
        for fk,fv in schema_element_filters:
          try:
            if getattr(se,fk) in fv:
              result.append(se_key)
          except AttributeError:
            pass
    else:
      result = list(avail_se)
    return result


  def tree(self,schema_element_class,schema_element_filters=None):
    """
    Returns a ldap.cidict.cidict dictionary representing the
    tree structure of the schema elements.
    """
    assert schema_element_class in [ObjectClass,AttributeType]
    avail_se = self.listall(schema_element_class,schema_element_filters)
    top_node = '_'
    tree = ldap.cidict.cidict({top_node:[]})
    # 1. Pass: Register all nodes
    for se in avail_se:
      tree[se] = []
    # 2. Pass: Register all sup references
    for se_oid in avail_se:
      se_obj = self.get_obj(schema_element_class,se_oid,None)
      if se_obj.__class__!=schema_element_class:
        # Ignore schema elements not matching schema_element_class.
        # This helps with falsely assigned OIDs.
        continue
      assert se_obj.__class__==schema_element_class, \
        "Schema element referenced by {} must be of class {} but was {}".format(
          se_oid,schema_element_class.__name__,se_obj.__class__
        )
      for s in se_obj.sup or ('_',):
        sup_oid = self.getoid(schema_element_class,s)
        try:
          tree[sup_oid].append(se_oid)
        except:
          pass
    return tree


  def getoid(self,se_class,nameoroid,raise_keyerror=0):
    """
    Get an OID by name or OID
    """
    nameoroid_stripped = nameoroid.split(';')[0].strip()
    if nameoroid_stripped in self.sed[se_class]:
      # name_or_oid is already a registered OID
      return nameoroid_stripped
    else:
      try:
        result_oid = self.name2oid[se_class][nameoroid_stripped]
      except KeyError:
        if raise_keyerror:
          raise KeyError('No registered {}-OID for nameoroid {}'.format(se_class.__name__,repr(nameoroid_stripped)))
        else:
          result_oid = nameoroid_stripped
    return result_oid


  def get_inheritedattr(self,se_class,nameoroid,name):
    """
    Get a possibly inherited attribute specified by name
    of a schema element specified by nameoroid.
    Returns None if class attribute is not set at all.

    Raises KeyError if no schema element is found by nameoroid.
    """
    se = self.sed[se_class][self.getoid(se_class,nameoroid)]
    try:
      result = getattr(se,name)
    except AttributeError:
      result = None
    if result is None and se.sup:
      result = self.get_inheritedattr(se_class,se.sup[0],name)
    return result


  def get_obj(self,se_class,nameoroid,default=None,raise_keyerror=0):
    """
    Get a schema element by name or OID
    """
    se_oid = self.getoid(se_class,nameoroid)
    try:
      se_obj = self.sed[se_class][se_oid]
    except KeyError:
      if raise_keyerror:
        raise KeyError('No ldap.schema.{} instance with nameoroid {} and se_oid {}'.format(
          se_class.__name__,repr(nameoroid),repr(se_oid))
        )
      else:
        se_obj = default
    return se_obj


  def get_inheritedobj(self,se_class,nameoroid,inherited=None):
    """
    Get a schema element by name or OID with all class attributes
    set including inherited class attributes
    """
    inherited = inherited or []
    se = copy.copy(self.sed[se_class].get(self.getoid(se_class,nameoroid)))
    if se and hasattr(se,'sup'):
      for class_attr_name in inherited:
        setattr(se,class_attr_name,self.get_inheritedattr(se_class,nameoroid,class_attr_name))
    return se


  def get_syntax(self,nameoroid):
    """
    Get the syntax of an attribute type specified by name or OID
    """
    at_oid = self.getoid(AttributeType,nameoroid)
    try:
      at_obj = self.get_inheritedobj(AttributeType,at_oid)
    except KeyError:
      return None
    else:
      return at_obj.syntax


  def get_structural_oc(self,oc_list):
    """
    Returns OID of structural object class in oc_list
    if any is present. Returns None else.
    """
    # Get tree of all STRUCTURAL object classes
    oc_tree = self.tree(ObjectClass,[('kind',[0])])
    # Filter all STRUCTURAL object classes
    struct_ocs = {}
    for oc_nameoroid in oc_list:
      oc_se = self.get_obj(ObjectClass,oc_nameoroid,None)
      if oc_se and oc_se.kind==0:
        struct_ocs[oc_se.oid] = None
    result = None
    # Build a copy of the oid list, to be cleaned as we go.
    struct_oc_list = list(struct_ocs)
    while struct_oc_list:
      oid = struct_oc_list.pop()
      for child_oid in oc_tree[oid]:
        if self.getoid(ObjectClass,child_oid) in struct_ocs:
          break
      else:
        result = oid
    return result


  def get_applicable_aux_classes(self,nameoroid):
    """
    Return a list of the applicable AUXILIARY object classes
    for a STRUCTURAL object class specified by 'nameoroid'
    if the object class is governed by a DIT content rule.
    If there's no DIT content rule all available AUXILIARY
    object classes are returned.
    """
    content_rule = self.get_obj(DITContentRule,nameoroid)
    if content_rule:
      # Return AUXILIARY object classes from DITContentRule instance
      return content_rule.aux
    else:
      # list all AUXILIARY object classes
      return self.listall(ObjectClass,[('kind',[2])])

  def attribute_types(
    self,object_class_list,attr_type_filter=None,raise_keyerror=1,ignore_dit_content_rule=0
  ):
    """
    Returns a 2-tuple of all must and may attributes including
    all inherited attributes of superior object classes
    by walking up classes along the SUP attribute.

    The attributes are stored in a ldap.cidict.cidict dictionary.

    object_class_list
        list of strings specifying object class names or OIDs
    attr_type_filter
        list of 2-tuples containing lists of class attributes
        which has to be matched
    raise_keyerror
        All KeyError exceptions for non-existent schema elements
        are ignored
    ignore_dit_content_rule
        A DIT content rule governing the structural object class
        is ignored
    """
    AttributeType = ldap.schema.AttributeType
    ObjectClass = ldap.schema.ObjectClass

    # Map object_class_list to object_class_oids (list of OIDs)
    object_class_oids = [
      self.getoid(ObjectClass,o)
      for o in object_class_list
    ]
    # Initialize
    oid_cache = {}

    r_must,r_may = ldap.cidict.cidict(),ldap.cidict.cidict()
    if '1.3.6.1.4.1.1466.101.120.111' in object_class_oids:
      # Object class 'extensibleObject' MAY carry every attribute type
      for at_obj in self.sed[AttributeType].values():
        r_may[at_obj.oid] = at_obj

    # Loop over OIDs of all given object classes
    while object_class_oids:
      object_class_oid = object_class_oids.pop(0)
      # Check whether the objectClass with this OID
      # has already been processed
      if object_class_oid in oid_cache:
        continue
      # Cache this OID as already being processed
      oid_cache[object_class_oid] = None
      try:
        object_class = self.sed[ObjectClass][object_class_oid]
      except KeyError:
        if raise_keyerror:
          raise
        # Ignore this object class
        continue
      assert isinstance(object_class,ObjectClass)
      assert hasattr(object_class,'must'),ValueError(object_class_oid)
      assert hasattr(object_class,'may'),ValueError(object_class_oid)
      for a in object_class.must:
        se_oid = self.getoid(AttributeType,a,raise_keyerror=raise_keyerror)
        r_must[se_oid] = self.get_obj(AttributeType,se_oid,raise_keyerror=raise_keyerror)
      for a in object_class.may:
        se_oid = self.getoid(AttributeType,a,raise_keyerror=raise_keyerror)
        r_may[se_oid] = self.get_obj(AttributeType,se_oid,raise_keyerror=raise_keyerror)

      object_class_oids.extend([
        self.getoid(ObjectClass,o)
        for o in object_class.sup
      ])

    # Process DIT content rules
    if not ignore_dit_content_rule:
      structural_oc = self.get_structural_oc(object_class_list)
      if structural_oc:
        # Process applicable DIT content rule
        try:
          dit_content_rule = self.get_obj(DITContentRule,structural_oc,raise_keyerror=1)
        except KeyError:
          # Not DIT content rule found for structural objectclass
          pass
        else:
          for a in dit_content_rule.must:
            se_oid = self.getoid(AttributeType,a,raise_keyerror=raise_keyerror)
            r_must[se_oid] = self.get_obj(AttributeType,se_oid,raise_keyerror=raise_keyerror)
          for a in dit_content_rule.may:
            se_oid = self.getoid(AttributeType,a,raise_keyerror=raise_keyerror)
            r_may[se_oid] = self.get_obj(AttributeType,se_oid,raise_keyerror=raise_keyerror)
          for a in dit_content_rule.nots:
            a_oid = self.getoid(AttributeType,a,raise_keyerror=raise_keyerror)
            try:
              del r_may[a_oid]
            except KeyError:
              pass

    # Remove all mandantory attribute types from
    # optional attribute type list
    for a in list(r_may):
      if a in r_must:
        del r_may[a]

    # Apply attr_type_filter to results
    if attr_type_filter:
      for l in [r_must,r_may]:
        for a in list(l):
          for afk,afv in attr_type_filter:
            try:
              schema_attr_type = self.sed[AttributeType][a]
            except KeyError:
              if raise_keyerror:
                raise KeyError('No attribute type found in sub schema by name %s' % (a))
              # If there's no schema element for this attribute type
              # but still KeyError is to be ignored we filter it away
              del l[a]
              break
            else:
              if not getattr(schema_attr_type,afk) in afv:
                del l[a]
                break

    return r_must,r_may # attribute_types()


def urlfetch(uri,trace_level=0):
  """
  Fetches a parsed schema entry by uri.

  If uri is a LDAP URL the LDAP server is queried directly.
  Otherwise uri is assumed to point to a LDIF file which
  is loaded with urllib.
  """
  uri = uri.strip()
  if uri.startswith(('ldap:', 'ldaps:', 'ldapi:')):
    ldap_url = ldapurl.LDAPUrl(uri)

    l=ldap.initialize(ldap_url.initializeUrl(),trace_level)
    l.protocol_version = ldap.VERSION3
    l.simple_bind_s(ldap_url.who or '', ldap_url.cred or '')
    subschemasubentry_dn = l.search_subschemasubentry_s(ldap_url.dn)
    if subschemasubentry_dn is None:
      s_temp = None
    else:
      if ldap_url.attrs is None:
        schema_attrs = SCHEMA_ATTRS
      else:
        schema_attrs = ldap_url.attrs
      s_temp = l.read_subschemasubentry_s(
        subschemasubentry_dn,attrs=schema_attrs
      )
    l.unbind_s()
    del l
  else:
    ldif_file = urlopen(uri)
    ldif_parser = ldif.LDIFRecordList(ldif_file,max_entries=1)
    ldif_parser.parse()
    subschemasubentry_dn,s_temp = ldif_parser.all_records[0]
  # Work-around for mixed-cased attribute names
  subschemasubentry_entry = ldap.cidict.cidict()
  s_temp = s_temp or {}
  for at,av in s_temp.items():
    if at in SCHEMA_CLASS_MAPPING:
      try:
        subschemasubentry_entry[at].extend(av)
      except KeyError:
        subschemasubentry_entry[at] = av
  # Finally parse the schema
  if subschemasubentry_dn!=None:
    parsed_sub_schema = ldap.schema.SubSchema(subschemasubentry_entry)
  else:
    parsed_sub_schema = None
  return subschemasubentry_dn, parsed_sub_schema
