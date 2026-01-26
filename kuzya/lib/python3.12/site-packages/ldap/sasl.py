"""
sasl.py - support for SASL mechanism

See https://www.python-ldap.org/ for details.

Description:
The ldap.sasl module provides SASL authentication classes.
Each class provides support for one SASL mechanism. This is done by
implementing a callback() - method, which will be called by the
LDAPObject's sasl_bind_s() method
Implementing support for new sasl mechanism is very easy --- see
the examples of digest_md5 and gssapi.
"""

from ldap import __version__

if __debug__:
    # Tracing is only supported in debugging mode
    from ldap import _trace_level, _trace_file


# These are the SASL callback id's , as defined in sasl.h
CB_USER = 0x4001
CB_AUTHNAME = 0x4002
CB_LANGUAGE = 0x4003
CB_PASS = 0x4004
CB_ECHOPROMPT = 0x4005
CB_NOECHOPROMPT = 0x4006
CB_GETREALM = 0x4008


class sasl:
    """
    This class handles SASL interactions for authentication.
    If an instance of this class is passed to ldap's sasl_bind_s()
    method, the library will call its callback() method. For
    specific SASL authentication mechanisms, this method can be
    overridden
    """

    def __init__(self, cb_value_dict, mech):
        """
        The (generic) base class takes a cb_value_dictionary of
        question-answer pairs. Questions are specified by the respective
        SASL callback id's. The mech argument is a string that specifies
        the SASL mechaninsm to be uesd.
        """
        self.cb_value_dict = cb_value_dict or {}
        if not isinstance(mech, bytes):
            mech = mech.encode('utf-8')
        self.mech = mech

    def callback(self, cb_id, challenge, prompt, defresult):
        """
        The callback method will be called by the sasl_bind_s()
        method several times. Each time it will provide the id, which
        tells us what kind of information is requested (the CB_*
        constants above). The challenge might be a short (English) text
        or some binary string, from which the return value is calculated.
        The prompt argument is always a human-readable description string;
        The defresult is a default value provided by the sasl library

        Currently, we do not use the challenge and prompt information, and
        return only information which is stored in the self.cb_value_dict
        cb_value_dictionary. Note that the current callback interface is not very
        useful for writing generic sasl GUIs, which would need to know all
        the questions to ask, before the answers are returned to the sasl
        lib (in contrast to one question at a time).

        Unicode strings are always converted to bytes.
        """

        # The following print command might be useful for debugging
        # new sasl mechanisms. So it is left here
        cb_result = self.cb_value_dict.get(cb_id, defresult) or ''
        if __debug__:
            if _trace_level >= 1:
                _trace_file.write("*** id=%d, challenge=%s, prompt=%s, defresult=%s\n-> %s\n" % (
                    cb_id,
                    challenge,
                    prompt,
                    repr(defresult),
                    repr(self.cb_value_dict.get(cb_result))
                ))
        if not isinstance(cb_result, bytes):
            cb_result = cb_result.encode('utf-8')
        return cb_result


class cram_md5(sasl):
    """
    This class handles SASL CRAM-MD5 authentication.
    """

    def __init__(self, authc_id, password, authz_id=""):
        auth_dict = {
            CB_AUTHNAME: authc_id,
            CB_PASS: password,
            CB_USER: authz_id,
        }
        sasl.__init__(self, auth_dict, "CRAM-MD5")


class digest_md5(sasl):
    """
    This class handles SASL DIGEST-MD5 authentication.
    """

    def __init__(self, authc_id, password, authz_id=""):
        auth_dict = {
            CB_AUTHNAME: authc_id,
            CB_PASS: password,
            CB_USER: authz_id,
        }
        sasl.__init__(self, auth_dict, "DIGEST-MD5")


class gssapi(sasl):
    """
    This class handles SASL GSSAPI (i.e. Kerberos V) authentication.
    """

    def __init__(self, authz_id=""):
        sasl.__init__(self, {CB_USER: authz_id}, "GSSAPI")


class external(sasl):
    """
    This class handles SASL EXTERNAL authentication
    (i.e. X.509 client certificate)
    """

    def __init__(self, authz_id=""):
        sasl.__init__(self, {CB_USER: authz_id}, "EXTERNAL")
