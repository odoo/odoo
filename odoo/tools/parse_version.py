# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

## this functions are taken from the setuptools package (version 0.6c8)
## http://peak.telecommunity.com/DevCenter/PkgResources#parsing-utilities

from __future__ import print_function
import re

from odoo.release import version
from odoo.tools import pycompat

component_re = re.compile(r'(\d+ | [a-z]+ | \.| -)', re.VERBOSE)
replace = {'pre':'c', 'preview':'c','-':'final-','_':'final-','rc':'c','dev':'@','saas':'','~':''}.get

def _parse_version_parts(s):
    for part in component_re.split(s):
        part = replace(part,part)
        if not part or part=='.':
            continue
        if part[:1] in '0123456789':
            yield part.zfill(8)    # pad for numeric comparison
        else:
            yield '*'+part

    yield '*final'  # ensure that alpha/beta/candidate are before final

def parse_version(s):
    """Convert a version string to a chronologically-sortable key

    This is a rough cross between distutils' StrictVersion and LooseVersion;
    if you give it versions that would work with StrictVersion, then it behaves
    the same; otherwise it acts like a slightly-smarter LooseVersion. It is
    *possible* to create pathological version coding schemes that will fool
    this parser, but they should be very rare in practice.

    The returned value will be a tuple of strings.  Numeric portions of the
    version are padded to 8 digits so they will compare numerically, but
    without relying on how numbers compare relative to strings.  Dots are
    dropped, but dashes are retained.  Trailing zeros between alpha segments
    or dashes are suppressed, so that e.g. "2.4.0" is considered the same as
    "2.4". Alphanumeric parts are lower-cased.

    The algorithm assumes that strings like "-" and any alpha string that
    alphabetically follows "final"  represents a "patch level".  So, "2.4-1"
    is assumed to be a branch or patch of "2.4", and therefore "2.4.1" is
    considered newer than "2.4-1", which in turn is newer than "2.4".

    Strings like "a", "b", "c", "alpha", "beta", "candidate" and so on (that
    come before "final" alphabetically) are assumed to be pre-release versions,
    so that the version "2.4" is considered newer than "2.4a1".

    Finally, to handle miscellaneous cases, the strings "pre", "preview", and
    "rc" are treated as if they were "c", i.e. as though they were release
    candidates, and therefore are not as new as a version string that does not
    contain them.
    """
    parts = []
    for part in _parse_version_parts((s or '0.1').lower()):
        if part.startswith('*'):
            if part<'*final':   # remove '-' before a prerelease tag
                while parts and parts[-1]=='*final-': parts.pop()
            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1]=='00000000':
                parts.pop()
        parts.append(part)
    return tuple(parts)


def version_match(valid_ranges, current=version):
    """Check if a version range matches the specified Odoo version.

    :param str valid_ranges:
        One or many version ranges. A range are 2 versions, separated by ``:``.
        The 1st one is the minimum version, and the 2nd one is the maximum.
        If any of the versions is empty, it will always match.
        Multiple ranges can be separated by ``,``.

        Examples that would return ``True``::

            version_match(":")
            version_match("12.0.0:,:15", "12.0")
            version_match("11.0:", "12.0")
            version_match(":13.0", "12.0")

        Check ``parse_version`` to know how those versions are parsed.

    :param str current:
        Target version to check against. It defaults to current Odoo version.

    :return bool:
        Indicates if Odoo version matches the range or not.
    """
    current_parsed = parse_version(current)
    for valid_range in valid_ranges.split(","):
        min_, max_ = valid_range.split(":")
        min_ = parse_version(min_) if min_ else current_parsed
        max_ = parse_version(max_) if max_ else current_parsed
        if not min_ <= current_parsed <= max_:
            return False
    return True


if __name__ == '__main__':
        def chk(lst, verbose=False):
            pvs = []
            for v in lst:
                pv = parse_version(v)
                pvs.append(pv)
                if verbose:
                    print(v, pv)

            for a, b in pycompat.izip(pvs, pvs[1:]):
                assert a < b, '%s < %s == %s' % (a, b, a < b)
        
        chk(('0', '4.2', '4.2.3.4', '5.0.0-alpha', '5.0.0-rc1', '5.0.0-rc1.1', '5.0.0_rc2', '5.0.0_rc3', '5.0.0'), False)
        chk(('5.0.0-0_rc3', '5.0.0-1dev', '5.0.0-1'), False) 
        
