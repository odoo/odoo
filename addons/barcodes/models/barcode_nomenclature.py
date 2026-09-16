import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.barcode import get_barcode_check_digit, is_barcode_encoding_valid

_logger = logging.getLogger(__name__)


UPC_EAN_CONVERSIONS = [
    ("none", "Never"),
    ("ean2upc", "EAN-13 to UPC-A"),
    ("upc2ean", "UPC-A to EAN-13"),
    ("always", "Always"),
]

# Number of dot-separated data fields each supported EPC URI scheme carries.
# The "-96"/"-198" tag encodings prefix the same data with a filter value.
URI_DATA_FIELDS = {
    "lgtin": 3,
    "sgtin": 3,
    "sgtin-96": 4,
    "sgtin-198": 4,
    "sscc": 2,
    "sscc-96": 3,
}

_ASCII_DIGITS = re.compile(r"\A[0-9]*\Z")
_NUMERIC_GROUP = re.compile(r"[{](?P<whole>N*)(?P<decimal>D*)[}]")

# `_match_pattern` runs a user-authored regex on every scan. Patterns are
# validated against catastrophic backtracking on write (`barcode.rule.
# _check_pattern`), but the subject is capped as well so that a pattern which
# slips through cannot turn one scan into unbounded CPU.
MAX_BARCODE_LENGTH = 256


class BarcodeNomenclature(models.Model):
    _name = "barcode.nomenclature"
    _description = "Barcode Nomenclature"

    name = fields.Char(
        string="Barcode Nomenclature",
        required=True,
        help="An internal identification of the barcode nomenclature",
    )
    rule_ids = fields.One2many(
        comodel_name="barcode.rule",
        inverse_name="barcode_nomenclature_id",
        string="Rules",
        help="The list of barcode rules",
    )
    upc_ean_conv = fields.Selection(
        selection=UPC_EAN_CONVERSIONS,
        string="UPC/EAN Conversion",
        default="always",
        required=True,
        help="UPC Codes can be converted to EAN by prefixing them with a zero. This setting determines if a UPC/EAN barcode should be automatically converted in one way or another when trying to match a rule with the other encoding.",
    )

    def _normalize_ean(self, ean):
        """Returns a valid zero padded EAN-13 from an EAN prefix.

        :type ean: str
        """
        ean = ean[0:13].zfill(13)
        return ean[0:-1] + str(get_barcode_check_digit(ean))

    def _normalize_upc(self, upc):
        """Returns a valid zero padded UPC-A from a UPC-A prefix.

        :type upc: str
        """
        return self._normalize_ean("0" + upc)[1:]

    def _match_pattern(self, barcode, pattern):
        """Checks barcode matches the pattern and retrieves the optional numeric value in barcode.

        :param barcode:
        :type barcode: str
        :param pattern:
        :type pattern: str
        :return: an object containing:
            - value: the numerical value encoded in the barcode (0 if no value encoded)
            - base_code: the barcode in which numerical content is replaced by 0's
            - match: boolean
        :rtype: dict
        """
        match = {
            "value": 0,
            "base_code": barcode,
            "match": False,
        }
        if len(barcode) > MAX_BARCODE_LENGTH:
            return match

        numeric_group = _NUMERIC_GROUP.search(pattern)
        if numeric_group:
            start = numeric_group.start()
            whole_size = len(numeric_group.group("whole"))
            decimal_size = len(numeric_group.group("decimal"))
            digits = barcode[start : start + whole_size + decimal_size]
            whole, decimal = digits[:whole_size], digits[whole_size:]
            # The slot must be filled with exactly as many ASCII digits as the
            # pattern declares. `str.isdigit` is not enough: it accepts
            # superscripts and other numerals that `int()` then rejects.
            if len(digits) != whole_size + decimal_size or not (
                _ASCII_DIGITS.match(whole) and _ASCII_DIGITS.match(decimal)
            ):
                return match
            match["value"] = int(whole or 0) + float(f"0.{decimal}" if decimal else 0)
            match["base_code"] = (
                barcode[:start]
                + (whole_size + decimal_size) * "0"
                + barcode[start + whole_size + decimal_size :]
            )
            pattern = (
                pattern[:start]
                + (whole_size + decimal_size) * "0"
                + pattern[numeric_group.end() :]
            )

        match["match"] = bool(re.match(pattern, match["base_code"]))
        return match

    def parse_barcode(self, barcode):
        """Parse a scanned barcode against this nomenclature.

        :param barcode:
        :type barcode: str
        :return: for an EPC URI, the list of data dicts it decodes to;
            otherwise a single dict, see :meth:`parse_nomenclature_barcode`.
        :rtype: dict | list[dict]
        """
        if len(self) > 1:
            raise ValueError(
                f"parse_barcode expects a single nomenclature, got {len(self)}"
            )
        if barcode.startswith("urn:"):
            return self._parse_uri(barcode)
        return self.parse_nomenclature_barcode(barcode)

    def parse_nomenclature_barcode(self, barcode):
        """Attempts to interpret and parse a barcode.

        :param barcode:
        :type barcode: str
        :return: A object containing various information about the barcode, like as:

            - code: the barcode
            - type: the barcode's type
            - value: if the id encodes a numerical value, it will be put there
            - base_code: the barcode code with all the encoding parts set to
              zero; the one put on the product in the backend

        :rtype: dict
        """
        # An `alias` rule restates the scan as another barcode, which must then
        # be parsed from the first rule again -- resuming at the next rule would
        # make the outcome depend on the alias rule's own sequence. `seen`
        # stops a cycle of aliases from looping forever.
        seen = set()
        while True:
            parsed_result = self._match_rules(barcode)
            if parsed_result["type"] != "alias":
                return parsed_result
            seen.add(barcode)
            barcode = parsed_result["code"]
            if barcode in seen:
                _logger.warning(
                    "Barcode nomenclature %r: alias cycle on %r, giving up.",
                    self.display_name,
                    barcode,
                )
                parsed_result["type"] = "error"
                return parsed_result

    def _match_rules(self, barcode):
        """Match `barcode` against this nomenclature's rules, once.

        Returns the same dict as :meth:`parse_nomenclature_barcode`, except that
        a matched ``alias`` rule yields ``type == "alias"`` with ``code`` set to
        the aliased barcode, for the caller to resolve.
        """
        parsed_result = {
            "encoding": "",
            "type": "error",
            "code": barcode,
            "base_code": barcode,
            "value": 0,
        }

        for rule in self.rule_ids:
            cur_barcode, converted = barcode, False
            # A UPC-A restated as EAN-13 always gains a leading zero, and
            # `is_barcode_encoding_valid` reads a leading zero as "this is really a
            # UPC-A". So the converted code can never validate as EAN-13: the
            # conversion has to stand in for the encoding check, not precede it.
            if (
                rule.encoding == "ean13"
                and self.upc_ean_conv in ("upc2ean", "always")
                and is_barcode_encoding_valid(barcode, "upca")
            ):
                cur_barcode, converted = "0" + barcode, True
            elif (
                rule.encoding == "upca"
                and self.upc_ean_conv in ("ean2upc", "always")
                and barcode[:1] == "0"
                and is_barcode_encoding_valid(barcode[1:], "upca")
            ):
                cur_barcode, converted = barcode[1:], True

            if not converted and not is_barcode_encoding_valid(barcode, rule.encoding):
                continue

            match = self._match_pattern(cur_barcode, rule.pattern)
            if not match["match"]:
                continue

            if rule.type == "alias":
                parsed_result["type"] = "alias"
                parsed_result["code"] = rule.alias
                return parsed_result

            parsed_result["encoding"] = rule.encoding
            parsed_result["type"] = rule.type
            parsed_result["value"] = match["value"]
            parsed_result["code"] = cur_barcode
            if rule.encoding == "ean13":
                parsed_result["base_code"] = self._normalize_ean(match["base_code"])
            elif rule.encoding == "upca":
                parsed_result["base_code"] = self._normalize_upc(match["base_code"])
            else:
                parsed_result["base_code"] = match["base_code"]
            return parsed_result

        return parsed_result

    # RFID/URI stuff.
    @api.model
    def _parse_uri(self, barcode):
        """Convert supported URI format (lgtin, sgtin, sgtin-96, sgtin-198,
        sscc and sscc-96) into a GS1 barcode.

        Every branch returns a list of data dicts -- callers rely on that shape
        (``len()``, ``[0]["type"]``, ...). A URI this method cannot decode is a
        failed parse, reported as an empty list rather than a raised exception:
        the argument is scanned input, so a malformed one is expected traffic.

        :param str barcode: the URI as a string.
        :rtype: list[dict]
        """
        parts = [part.strip() for part in barcode.split(":")]
        # urn:<namespace>:<type>:<identifier>:<data>
        if len(parts) != 5:
            _logger.info(
                "Malformed EPC URI %r: expected 5 ':'-separated parts.", barcode
            )
            return []
        identifier, data = parts[3], parts[4].split(".")

        expected = URI_DATA_FIELDS.get(identifier)
        if expected is None:
            _logger.info(
                "Unrecognized URI identifier %r in barcode %r", identifier, barcode
            )
            return []
        if len(data) != expected:
            _logger.info(
                "Malformed EPC URI %r: %r expects %d '.'-separated fields, got %d.",
                barcode,
                identifier,
                expected,
                len(data),
            )
            return []
        # The "-96"/"-198" tag encodings prefix the data with a filter value.
        if identifier in ("sgtin-96", "sgtin-198", "sscc-96"):
            data = data[1:]
        # Only the two leading fields feed the check-digit computation; an
        # SGTIN-198 serial is legitimately alphanumeric and is passed through.
        if not all(field and _ASCII_DIGITS.match(field) for field in data[:2]):
            _logger.info(
                "Malformed EPC URI %r: company prefix and reference must be digits.",
                barcode,
            )
            return []

        if identifier.startswith("sscc"):
            return self._convert_uri_sscc_data_into_package(barcode, data)
        return self._convert_uri_gtin_data_into_tracking_number(barcode, data)

    @api.model
    def _convert_uri_gtin_data_into_tracking_number(self, base_code, data):
        gs1_company_prefix, item_ref_and_indicator, tracking_number = data
        indicator = item_ref_and_indicator[0]
        item_ref = item_ref_and_indicator[1:]
        product_barcode = indicator + gs1_company_prefix + item_ref
        product_barcode += str(get_barcode_check_digit(product_barcode + "0"))
        return [
            {
                "base_code": base_code,
                "code": product_barcode,
                "encoding": "",
                "type": "product",
                "value": product_barcode,
            },
            {
                "base_code": base_code,
                "code": tracking_number,
                "encoding": "",
                "type": "lot",
                "value": tracking_number,
            },
        ]

    @api.model
    def _convert_uri_sscc_data_into_package(self, base_code, data):
        gs1_company_prefix, serial_reference = data
        extension = serial_reference[0]
        serial_ref = serial_reference[1:]
        sscc = extension + gs1_company_prefix + serial_ref
        sscc += str(get_barcode_check_digit(sscc + "0"))
        return [
            {
                "base_code": base_code,
                "code": sscc,
                "encoding": "",
                "type": "package",
                "value": sscc,
            }
        ]

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default(self):
        default_record = self.env.ref(
            "barcodes.default_barcode_nomenclature", raise_if_not_found=False
        )
        if default_record and default_record in self:
            raise UserError(
                _(
                    "You cannot delete '%(name)s' because it's the default barcode nomenclature.",
                    name=default_record.display_name,
                )
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_by_company(self):
        """Refuse to delete a nomenclature a company is still scanning with.

        `res.company.nomenclature_id` is a plain Many2one, so the default
        `ondelete="set null"` used to empty it silently. Nothing raised, and
        nothing pointed at the deletion: every subsequent scan simply parsed
        against no rules and came back `type: "error"`.
        """
        companies = (
            self.env["res.company"].sudo().search([("nomenclature_id", "in", self.ids)])
        )
        if companies:
            raise UserError(
                _(
                    "You cannot delete the barcode nomenclature %(names)s because "
                    "it is still used by: %(companies)s.",
                    names=", ".join(
                        (self & companies.nomenclature_id).mapped("display_name")
                    ),
                    companies=", ".join(companies.mapped("display_name")),
                )
            )
