"""Definitions for constants exported by OpenLDAP

This file lists all constants we know about, even those that aren't
available in the OpenLDAP version python-ldap is compiled against.

The information serves two purposes:

- Generate a C header with the constants
- Provide support for building documentation without compiling python-ldap

"""

# This module cannot import anything from ldap.
# When building documentation, it is used to initialize ldap.__init__.


class Constant:
    """Base class for a definition of an OpenLDAP constant
    """

    def __init__(self, name, optional=False, requirements=(), doc=None):
        self.name = name
        if optional:
            self_requirement = f'defined(LDAP_{self.name})'
            requirements = list(requirements) + [self_requirement]
        self.requirements = requirements
        self.doc = self.__doc__ = doc


class Error(Constant):
    """Definition for an OpenLDAP error code

    This is a constant at the C level; in Python errors are provided as
    exception classes.
    """

    c_template = 'add_err({self.name});'


class Int(Constant):
    """Definition for an OpenLDAP integer constant"""

    c_template = 'add_int({self.name});'


class TLSInt(Int):
    """Definition for a TLS integer constant -- requires HAVE_TLS"""

    def __init__(self, *args, **kwargs):
        requrements = list(kwargs.get('requirements', ()))
        kwargs['requirements'] = ['HAVE_TLS'] + requrements
        super().__init__(*args, **kwargs)


class Feature(Constant):
    """Definition for a feature: 0 or 1 based on a C #ifdef

    """

    c_template = '\n'.join([
        '',
        '#ifdef {self.c_feature}',
        'if (PyModule_AddIntConstant(m, "{self.name}", 1) != 0) return -1;',
        '#else',
        'if (PyModule_AddIntConstant(m, "{self.name}", 0) != 0) return -1;',
        '#endif',
        '',
    ])


    def __init__(self, name, c_feature, **kwargs):
        super().__init__(name, **kwargs)
        self.c_feature = c_feature


class Str(Constant):
    c_template = 'add_string({self.name});'


API_2004 = 'LDAP_API_VERSION >= 2004'

CONSTANTS = (
    Error('ADMINLIMIT_EXCEEDED'),
    Error('AFFECTS_MULTIPLE_DSAS'),
    Error('ALIAS_DEREF_PROBLEM'),
    Error('ALIAS_PROBLEM'),
    Error('ALREADY_EXISTS'),
    Error('AUTH_METHOD_NOT_SUPPORTED'),
    Error('AUTH_UNKNOWN'),
    Error('BUSY'),
    Error('CLIENT_LOOP'),
    Error('COMPARE_FALSE'),
    Error('COMPARE_TRUE'),
    Error('CONFIDENTIALITY_REQUIRED'),
    Error('CONNECT_ERROR'),
    Error('CONSTRAINT_VIOLATION'),
    Error('CONTROL_NOT_FOUND'),
    Error('DECODING_ERROR'),
    Error('ENCODING_ERROR'),
    Error('FILTER_ERROR'),
    Error('INAPPROPRIATE_AUTH'),
    Error('INAPPROPRIATE_MATCHING'),
    Error('INSUFFICIENT_ACCESS'),
    Error('INVALID_CREDENTIALS'),
    Error('INVALID_DN_SYNTAX'),
    Error('INVALID_SYNTAX'),
    Error('IS_LEAF'),
    Error('LOCAL_ERROR'),
    Error('LOOP_DETECT'),
    Error('MORE_RESULTS_TO_RETURN'),
    Error('NAMING_VIOLATION'),
    Error('NO_MEMORY'),
    Error('NO_OBJECT_CLASS_MODS'),
    Error('NO_OBJECT_CLASS_MODS'),
    Error('NO_RESULTS_RETURNED'),
    Error('NO_SUCH_ATTRIBUTE'),
    Error('NO_SUCH_OBJECT'),
    Error('NOT_ALLOWED_ON_NONLEAF'),
    Error('NOT_ALLOWED_ON_RDN'),
    Error('NOT_SUPPORTED'),
    Error('OBJECT_CLASS_VIOLATION'),
    Error('OPERATIONS_ERROR'),
    Error('OTHER'),
    Error('PARAM_ERROR'),
    Error('PARTIAL_RESULTS'),
    Error('PROTOCOL_ERROR'),
    Error('REFERRAL'),
    Error('REFERRAL_LIMIT_EXCEEDED'),
    Error('RESULTS_TOO_LARGE'),
    Error('SASL_BIND_IN_PROGRESS'),
    Error('SERVER_DOWN'),
    Error('SIZELIMIT_EXCEEDED'),
    Error('STRONG_AUTH_NOT_SUPPORTED'),
    Error('STRONG_AUTH_REQUIRED'),
    Error('SUCCESS'),
    Error('TIMELIMIT_EXCEEDED'),
    Error('TIMEOUT'),
    Error('TYPE_OR_VALUE_EXISTS'),
    Error('UNAVAILABLE'),
    Error('UNAVAILABLE_CRITICAL_EXTENSION'),
    Error('UNDEFINED_TYPE'),
    Error('UNWILLING_TO_PERFORM'),
    Error('USER_CANCELLED'),
    Error('VLV_ERROR'),
    Error('X_PROXY_AUTHZ_FAILURE'),

    Error('CANCELLED', requirements=['defined(LDAP_API_FEATURE_CANCEL)']),
    Error('NO_SUCH_OPERATION', requirements=['defined(LDAP_API_FEATURE_CANCEL)']),
    Error('TOO_LATE', requirements=['defined(LDAP_API_FEATURE_CANCEL)']),
    Error('CANNOT_CANCEL', requirements=['defined(LDAP_API_FEATURE_CANCEL)']),

    Error('ASSERTION_FAILED', optional=True),

    Error('PROXIED_AUTHORIZATION_DENIED', optional=True),

    # simple constants

    Int('API_VERSION'),
    Int('VENDOR_VERSION'),

    Int('PORT'),
    Int('VERSION1'),
    Int('VERSION2'),
    Int('VERSION3'),
    Int('VERSION_MIN'),
    Int('VERSION'),
    Int('VERSION_MAX'),
    Int('TAG_MESSAGE'),
    Int('TAG_MSGID'),

    Int('REQ_BIND'),
    Int('REQ_UNBIND'),
    Int('REQ_SEARCH'),
    Int('REQ_MODIFY'),
    Int('REQ_ADD'),
    Int('REQ_DELETE'),
    Int('REQ_MODRDN'),
    Int('REQ_COMPARE'),
    Int('REQ_ABANDON'),

    Int('TAG_LDAPDN'),
    Int('TAG_LDAPCRED'),
    Int('TAG_CONTROLS'),
    Int('TAG_REFERRAL'),

    Int('REQ_EXTENDED'),
    Int('TAG_NEWSUPERIOR', requirements=[API_2004]),
    Int('TAG_EXOP_REQ_OID', requirements=[API_2004]),
    Int('TAG_EXOP_REQ_VALUE', requirements=[API_2004]),
    Int('TAG_EXOP_RES_OID', requirements=[API_2004]),
    Int('TAG_EXOP_RES_VALUE', requirements=[API_2004]),
    Int('TAG_SASL_RES_CREDS', requirements=[API_2004, 'defined(HAVE_SASL)']),

    Int('SASL_AUTOMATIC'),
    Int('SASL_INTERACTIVE'),
    Int('SASL_QUIET'),

    # reversibles

    Int('RES_BIND'),
    Int('RES_SEARCH_ENTRY'),
    Int('RES_SEARCH_RESULT'),
    Int('RES_MODIFY'),
    Int('RES_ADD'),
    Int('RES_DELETE'),
    Int('RES_MODRDN'),
    Int('RES_COMPARE'),
    Int('RES_ANY'),

    Int('RES_SEARCH_REFERENCE'),
    Int('RES_EXTENDED'),
    Int('RES_UNSOLICITED'),

    Int('RES_INTERMEDIATE'),

    # non-reversibles

    Int('AUTH_NONE'),
    Int('AUTH_SIMPLE'),
    Int('SCOPE_BASE'),
    Int('SCOPE_ONELEVEL'),
    Int('SCOPE_SUBTREE'),
    Int('SCOPE_SUBORDINATE', optional=True),
    Int('MOD_ADD'),
    Int('MOD_DELETE'),
    Int('MOD_REPLACE'),
    Int('MOD_INCREMENT'),
    Int('MOD_BVALUES'),

    Int('MSG_ONE'),
    Int('MSG_ALL'),
    Int('MSG_RECEIVED'),

    # (error constants handled above)

    Int('DEREF_NEVER'),
    Int('DEREF_SEARCHING'),
    Int('DEREF_FINDING'),
    Int('DEREF_ALWAYS'),
    Int('NO_LIMIT'),

    Int('OPT_API_INFO'),
    Int('OPT_DEREF'),
    Int('OPT_SIZELIMIT'),
    Int('OPT_TIMELIMIT'),
    Int('OPT_REFERRALS', optional=True),
    Int('OPT_RESULT_CODE'),
    Int('OPT_ERROR_NUMBER'),
    Int('OPT_RESTART'),
    Int('OPT_PROTOCOL_VERSION'),
    Int('OPT_SERVER_CONTROLS'),
    Int('OPT_CLIENT_CONTROLS'),
    Int('OPT_API_FEATURE_INFO'),
    Int('OPT_HOST_NAME'),

    Int('OPT_DESC'),
    Int('OPT_DIAGNOSTIC_MESSAGE'),

    Int('OPT_ERROR_STRING'),
    Int('OPT_MATCHED_DN'),
    Int('OPT_DEBUG_LEVEL'),
    Int('OPT_TIMEOUT'),
    Int('OPT_REFHOPLIMIT'),
    Int('OPT_NETWORK_TIMEOUT'),
    Int('OPT_TCP_USER_TIMEOUT', optional=True),
    Int('OPT_URI'),

    Int('OPT_DEFBASE', optional=True),

    TLSInt('OPT_X_TLS', optional=True),
    TLSInt('OPT_X_TLS_CTX'),
    TLSInt('OPT_X_TLS_CACERTFILE'),
    TLSInt('OPT_X_TLS_CACERTDIR'),
    TLSInt('OPT_X_TLS_CERTFILE'),
    TLSInt('OPT_X_TLS_KEYFILE'),
    TLSInt('OPT_X_TLS_REQUIRE_CERT'),
    TLSInt('OPT_X_TLS_CIPHER_SUITE'),
    TLSInt('OPT_X_TLS_RANDOM_FILE'),
    TLSInt('OPT_X_TLS_DHFILE'),
    TLSInt('OPT_X_TLS_NEVER'),
    TLSInt('OPT_X_TLS_HARD'),
    TLSInt('OPT_X_TLS_DEMAND'),
    TLSInt('OPT_X_TLS_ALLOW'),
    TLSInt('OPT_X_TLS_TRY'),

    TLSInt('OPT_X_TLS_VERSION', optional=True),
    TLSInt('OPT_X_TLS_CIPHER', optional=True),
    TLSInt('OPT_X_TLS_PEERCERT', optional=True),

    # only available if OpenSSL supports it => might cause
    # backward compatibility problems
    TLSInt('OPT_X_TLS_CRLCHECK', optional=True),

    TLSInt('OPT_X_TLS_CRLFILE', optional=True),

    TLSInt('OPT_X_TLS_CRL_NONE'),
    TLSInt('OPT_X_TLS_CRL_PEER'),
    TLSInt('OPT_X_TLS_CRL_ALL'),
    TLSInt('OPT_X_TLS_NEWCTX', optional=True),
    TLSInt('OPT_X_TLS_PROTOCOL_MIN', optional=True),
    TLSInt('OPT_X_TLS_PACKAGE', optional=True),

    # Added in OpenLDAP 2.4.52
    TLSInt('OPT_X_TLS_ECNAME', optional=True),
    TLSInt('OPT_X_TLS_REQUIRE_SAN', optional=True),

    # Added in OpenLDAP 2.5
    TLSInt('OPT_X_TLS_PEERCERT', optional=True),
    TLSInt('OPT_X_TLS_PROTOCOL_MAX', optional=True),

    TLSInt('OPT_X_TLS_PROTOCOL_SSL3', optional=True),
    TLSInt('OPT_X_TLS_PROTOCOL_TLS1_0', optional=True),
    TLSInt('OPT_X_TLS_PROTOCOL_TLS1_1', optional=True),
    TLSInt('OPT_X_TLS_PROTOCOL_TLS1_2', optional=True),
    TLSInt('OPT_X_TLS_PROTOCOL_TLS1_3', optional=True),

    Int('OPT_X_SASL_MECH'),
    Int('OPT_X_SASL_REALM'),
    Int('OPT_X_SASL_AUTHCID'),
    Int('OPT_X_SASL_AUTHZID'),
    Int('OPT_X_SASL_SSF'),
    Int('OPT_X_SASL_SSF_EXTERNAL'),
    Int('OPT_X_SASL_SECPROPS'),
    Int('OPT_X_SASL_SSF_MIN'),
    Int('OPT_X_SASL_SSF_MAX'),
    Int('OPT_X_SASL_NOCANON', optional=True),
    Int('OPT_X_SASL_USERNAME', optional=True),
    Int('OPT_CONNECT_ASYNC', optional=True),
    Int('OPT_X_KEEPALIVE_IDLE', optional=True),
    Int('OPT_X_KEEPALIVE_PROBES', optional=True),
    Int('OPT_X_KEEPALIVE_INTERVAL', optional=True),

    Int('DN_FORMAT_LDAP'),
    Int('DN_FORMAT_LDAPV3'),
    Int('DN_FORMAT_LDAPV2'),
    Int('DN_FORMAT_DCE'),
    Int('DN_FORMAT_UFN'),
    Int('DN_FORMAT_AD_CANONICAL'),
    # Int('DN_FORMAT_LBER'),  # for testing only
    Int('DN_FORMAT_MASK'),
    Int('DN_PRETTY'),
    Int('DN_SKIP'),
    Int('DN_P_NOLEADTRAILSPACES'),
    Int('DN_P_NOSPACEAFTERRDN'),
    Int('DN_PEDANTIC'),

    Int('AVA_NULL'),
    Int('AVA_STRING'),
    Int('AVA_BINARY'),
    Int('AVA_NONPRINTABLE'),

    Int('OPT_SUCCESS'),

    # XXX - these should be errors
    Int('URL_ERR_BADSCOPE'),
    Int('URL_ERR_MEM'),

    Feature('SASL_AVAIL', 'HAVE_SASL'),
    Feature('TLS_AVAIL', 'HAVE_TLS'),
    Feature('INIT_FD_AVAIL', 'HAVE_LDAP_INIT_FD'),

    Str("CONTROL_MANAGEDSAIT"),
    Str("CONTROL_PROXY_AUTHZ"),
    Str("CONTROL_SUBENTRIES"),
    Str("CONTROL_VALUESRETURNFILTER"),
    Str("CONTROL_ASSERT"),
    Str("CONTROL_PRE_READ"),
    Str("CONTROL_POST_READ"),
    Str("CONTROL_SORTREQUEST"),
    Str("CONTROL_SORTRESPONSE"),
    Str("CONTROL_PAGEDRESULTS"),
    Str("CONTROL_SYNC"),
    Str("CONTROL_SYNC_STATE"),
    Str("CONTROL_SYNC_DONE"),
    Str("SYNC_INFO"),
    Str("CONTROL_PASSWORDPOLICYREQUEST"),
    Str("CONTROL_PASSWORDPOLICYRESPONSE"),
    Str("CONTROL_RELAX"),
)


def print_header():  # pragma: no cover
    """Print the C header file to standard output"""

    print('/*')
    print(' * Generated with:')
    print(' *   python Lib/ldap/constants.py > Modules/constants_generated.h')
    print(' *')
    print(' * Please do any modifications there, then re-generate this file')
    print(' */')
    print('')

    current_requirements = []

    def pop_requirement():
        popped = current_requirements.pop()
        print('#endif')
        print()

    for definition in CONSTANTS:
        while not set(current_requirements).issubset(definition.requirements):
            pop_requirement()

        for requirement in definition.requirements:
            if requirement not in current_requirements:
                current_requirements.append(requirement)
                print()
                print(f'#if {requirement}')

        print(definition.c_template.format(self=definition))

    while current_requirements:
        pop_requirement()


if __name__ == '__main__':
    print_header()
