"""
ldap.resiter - processing LDAP results with iterators

See https://www.python-ldap.org/ for details.
"""

from ldap.pkginfo import __version__, __author__, __license__


class ResultProcessor:
    """
    Mix-in class used with ldap.ldapopbject.LDAPObject or derived classes.
    """

    def allresults(self, msgid, timeout=-1, add_ctrls=0):
        """
        Generator function which returns an iterator for processing all LDAP operation
        results of the given msgid like retrieved with LDAPObject.result3() -> 4-tuple
        """
        result_type, result_list, result_msgid, result_serverctrls, _, _ = \
            self.result4(
                msgid,
                0,
                timeout,
                add_ctrls=add_ctrls
            )
        while result_type and result_list:
            yield (
                result_type,
                result_list,
                result_msgid,
                result_serverctrls
            )
            result_type, result_list, result_msgid, result_serverctrls, _, _ = \
                self.result4(
                    msgid,
                    0,
                    timeout,
                    add_ctrls=add_ctrls
                )
        return # allresults()
