import datetime

from odoo import api, models

# Value of each character in the CURP check-digit sum. Ñ sits between N and O,
# which is why this cannot be a plain ASCII index.
_CURP_ALPHABET = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"

# The two RFCs the SAT issues for everyone at once: sales to the general public
# and to a foreign resident. They are structurally valid and deliberately
# shared, so they are exempt from nothing except being anybody's own.
_GENERIC_RFC = frozenset({"XAXX010101000", "XEXX010101000"})


class ResPartnerIdentifierType(models.Model):
    _inherit = "res.partner.identifier.type"

    @api.model
    def _get_code_checkers(self):
        return super()._get_code_checkers() | {
            "mx_rfc": self._check_code_mx_rfc,
            "mx_curp": self._check_code_mx_curp,
        }

    def _check_code_mx_rfc(self, value):
        """The RFC's embedded birth or incorporation date must be a real one.

        Structure is already settled by the type's own format. What a regular
        expression cannot say is that 970231 is not a date, and a transposed
        pair of digits is the commonest way an RFC is mistyped.

        No check digit is verified. The homoclave's is computable, but RFCs
        issued before the algorithm was standardised do not all satisfy it, and
        refusing a taxpayer's real RFC is worse than accepting a wrong one.
        """
        if value in _GENERIC_RFC:
            return True
        offset = 3 if len(value) == 12 else 4
        return self._is_real_date(value[offset : offset + 6])

    def _check_code_mx_curp(self, value):
        """The CURP's date must be real and its check digit must agree.

        Unlike the RFC, every CURP has been issued by one authority under one
        algorithm, so the check digit can be relied on: it catches a single
        mistyped character, which is what it exists for.
        """
        if not self._is_real_date(value[4:10]):
            return False
        return value[17] == str(self._curp_check_digit(value[:17]))

    @staticmethod
    def _curp_check_digit(first_seventeen):
        """RENAPO's check digit: a position-weighted sum, mod 10, complemented."""
        total = sum(
            _CURP_ALPHABET.index(char) * (18 - position)
            for position, char in enumerate(first_seventeen)
        )
        return (10 - total % 10) % 10

    @staticmethod
    def _is_real_date(yymmdd):
        """Whether YYMMDD names a day that exists, in either century.

        The two digits do not say which century, and neither identifier
        records it, so a date is accepted when it is real in one of them --
        29 February included, which is exactly the case a naive range check
        gets wrong.
        """
        try:
            year, month, day = (
                int(yymmdd[0:2]),
                int(yymmdd[2:4]),
                int(yymmdd[4:6]),
            )
        except ValueError:
            return False
        for century in (1900, 2000):
            try:
                datetime.date(century + year, month, day)
            except ValueError:
                continue
            return True
        return False
