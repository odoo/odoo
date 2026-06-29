"""VAT validation utilities using python-stdnum library."""
import logging
import re

from stdnum import util as stdnum_util
from stdnum.exceptions import ValidationError
from stdnum.fr import siren as stdnum_siren
from stdnum.fr import siret as stdnum_siret

_logger = logging.getLogger(__name__)

_VAT_PREFIX_RE = re.compile(r'^([A-Za-z]{2})(.+)$')


def _normalize_candidates(vat, country_code=None):
    """Yield country codes to try for VAT validation."""
    candidates = []
    if country_code:
        candidates.append(country_code.lower())
    if match := _VAT_PREFIX_RE.match(vat):
        candidates.append(match.group(1).lower())
    seen = set()
    for code in candidates:
        if code and code not in seen:
            seen.add(code)
            yield code


def is_valid_vat(vat, country_code=None):
    """Return True when the provided VAT number is recognised by python-stdnum."""
    if not vat:
        return False
    if not stdnum_util:
        _logger.warning('python-stdnum not available, cannot validate VAT number: %s', vat)
        return False
    normalized = stdnum_util.clean(vat, ' -./').strip().upper()
    if not normalized:
        return False
    for candidate_code in _normalize_candidates(normalized, country_code):
        try:
            module = stdnum_util.get_cc_module(candidate_code, 'vat')
        except (ImportError, AttributeError, KeyError):
            continue
        validator = None
        if module:
            try:
                validator = module.is_valid
            except AttributeError:
                validator = None
        if not validator:
            continue
        try:
            if validator(normalized):
                return True
        except ValidationError:
            continue
    return False


def is_valid_french_registration(value):
    """Return True when the provided value is a valid French SIREN/SIRET."""
    if not value:
        return False
    cleaned = stdnum_util.clean(value, ' -./').strip()
    if not cleaned or not cleaned.isdigit():
        return False
    length = len(cleaned)
    if length == 14:
        try:
            return stdnum_siret.is_valid(cleaned)
        except ValidationError:
            return False
    if length == 9:
        try:
            return stdnum_siren.is_valid(cleaned)
        except ValidationError:
            return False
    return False
