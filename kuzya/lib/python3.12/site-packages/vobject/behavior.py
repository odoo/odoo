from . import base


#------------------------ Abstract class for behavior --------------------------
class Behavior(object):
    """
    Behavior (validation, encoding, and transformations) for vobjects.

    Abstract class to describe vobject options, requirements and encodings.

    Behaviors are used for root components like VCALENDAR, for subcomponents
    like VEVENT, and for individual lines in components.

    Behavior subclasses are not meant to be instantiated, all methods should
    be classmethods.

    @cvar name:
        The uppercase name of the object described by the class, or a generic
        name if the class defines behavior for many objects.
    @cvar description:
        A brief excerpt from the RFC explaining the function of the component or
        line.
    @cvar versionString:
        The string associated with the component, for instance, 2.0 if there's a
        line like VERSION:2.0, an empty string otherwise.
    @cvar knownChildren:
        A dictionary with uppercased component/property names as keys and a
        tuple (min, max, id) as value, where id is the id used by
        L{registerBehavior}, min and max are the limits on how many of this child
        must occur.  None is used to denote no max or no id.
    @cvar quotedPrintable:
        A boolean describing whether the object should be encoded and decoded
        using quoted printable line folding and character escaping.
    @cvar defaultBehavior:
        Behavior to apply to ContentLine children when no behavior is found.
    @cvar hasNative:
        A boolean describing whether the object can be transformed into a more
        Pythonic object.
    @cvar isComponent:
        A boolean, True if the object should be a Component.
    @cvar sortFirst:
        The lower-case list of children which should come first when sorting.
    @cvar allowGroup:
        Whether or not vCard style group prefixes are allowed.
    """
    name = ''
    description = ''
    versionString = ''
    knownChildren = {}
    quotedPrintable = False
    defaultBehavior = None
    hasNative = False
    isComponent = False
    allowGroup = False
    forceUTC = False
    sortFirst = []

    def __init__(self):
        err = "Behavior subclasses are not meant to be instantiated"
        raise base.VObjectError(err)

    @classmethod
    def validate(cls, obj, raiseException=False, complainUnrecognized=False):
        """Check if the object satisfies this behavior's requirements.

        @param obj:
            The L{ContentLine<base.ContentLine>} or
            L{Component<base.Component>} to be validated.
        @param raiseException:
            If True, raise a L{base.ValidateError} on validation failure.
            Otherwise return a boolean.
        @param complainUnrecognized:
            If True, fail to validate if an uncrecognized parameter or child is
            found.  Otherwise log the lack of recognition.

        """
        if not cls.allowGroup and obj.group is not None:
            err = "{0} has a group, but this object doesn't support groups".format(obj)
            raise base.VObjectError(err)
        if isinstance(obj, base.ContentLine):
            return cls.lineValidate(obj, raiseException, complainUnrecognized)
        elif isinstance(obj, base.Component):
            count = {}
            for child in obj.getChildren():
                if not child.validate(raiseException, complainUnrecognized):
                    return False
                name = child.name.upper()
                count[name] = count.get(name, 0) + 1
            for key, val in cls.knownChildren.items():
                if count.get(key, 0) < val[0]:
                    if raiseException:
                        m = "{0} components must contain at least {1} {2}"
                        raise base.ValidateError(m .format(cls.name, val[0], key))
                    return False
                if val[1] and count.get(key, 0) > val[1]:
                    if raiseException:
                        m = "{0} components cannot contain more than {1} {2}"
                        raise base.ValidateError(m.format(cls.name, val[1], key))
                    return False
            return True
        else:
            err = "{0} is not a Component or Contentline".format(obj)
            raise base.VObjectError(err)

    @classmethod
    def lineValidate(cls, line, raiseException, complainUnrecognized):
        """Examine a line's parameters and values, return True if valid."""
        return True

    @classmethod
    def decode(cls, line):
        if line.encoded:
            line.encoded = 0

    @classmethod
    def encode(cls, line):
        if not line.encoded:
            line.encoded = 1

    @classmethod
    def transformToNative(cls, obj):
        """
        Turn a ContentLine or Component into a Python-native representation.

        If appropriate, turn dates or datetime strings into Python objects.
        Components containing VTIMEZONEs turn into VtimezoneComponents.

        """
        return obj

    @classmethod
    def transformFromNative(cls, obj):
        """
        Inverse of transformToNative.
        """
        raise base.NativeError("No transformFromNative defined")

    @classmethod
    def generateImplicitParameters(cls, obj):
        """Generate any required information that don't yet exist."""
        pass

    @classmethod
    def serialize(cls, obj, buf, lineLength, validate=True):
        """
        Set implicit parameters, do encoding, return unicode string.

        If validate is True, raise VObjectError if the line doesn't validate
        after implicit parameters are generated.

        Default is to call base.defaultSerialize.

        """

        cls.generateImplicitParameters(obj)
        if validate:
            cls.validate(obj, raiseException=True)

        if obj.isNative:
            transformed = obj.transformFromNative()
            undoTransform = True
        else:
            transformed = obj
            undoTransform = False

        out = base.defaultSerialize(transformed, buf, lineLength)
        if undoTransform:
            obj.transformToNative()
        return out

    @classmethod
    def valueRepr(cls, line):
        """return the representation of the given content line value"""
        return line.value
