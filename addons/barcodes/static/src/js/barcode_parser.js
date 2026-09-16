/** @odoo-module native */

// Number of dot-separated data fields each supported EPC URI scheme carries.
// The "-96"/"-198" tag encodings prefix the same data with a filter value.
const URI_DATA_FIELDS = {
    lgtin: 3,
    sgtin: 3,
    "sgtin-96": 4,
    "sgtin-198": 4,
    sscc: 2,
    "sscc-96": 3,
};
const FILTERED_URI_SCHEMES = ["sgtin-96", "sgtin-198", "sscc-96"];

const ASCII_DIGITS = /^[0-9]*$/;
const NUMERIC_GROUP = /[{](N*)(D*)[}]/;

// Mirrors `barcode.nomenclature.MAX_BARCODE_LENGTH`.
const MAX_BARCODE_LENGTH = 256;

export class BarcodeParser {
    static barcodeNomenclatureFields = ["name", "rule_ids", "upc_ean_conv"];
    static barcodeRuleFields = [
        "name",
        "sequence",
        "type",
        "encoding",
        "pattern",
        "alias",
    ];
    static async fetchNomenclature(orm, id) {
        const [nomenclature] = await orm.read(
            "barcode.nomenclature",
            [id],
            this.barcodeNomenclatureFields,
        );
        let rules = await orm.searchRead(
            "barcode.rule",
            [["barcode_nomenclature_id", "=", id]],
            this.barcodeRuleFields,
        );
        rules = rules.sort((a, b) => a.sequence - b.sequence);
        nomenclature.rules = rules;
        return nomenclature;
    }

    constructor() {
        this.setup(...arguments);
    }

    setup({ nomenclature }) {
        this.nomenclature = nomenclature;
    }

    /**
     * This algorithm is identical for all fixed length numeric GS1 data structures.
     *
     * It is also valid for EAN-8, EAN-12 (UPC-A), EAN-13 check digit after sanitizing.
     * https://www.gs1.org/sites/default/files/docs/barcodes/GS1_General_Specifications.pdf
     *
     * @param {String} numericBarcode
     * @returns {number} Check Digit
     */
    get_barcode_check_digit(numericBarcode) {
        let oddsum = 0,
            evensum = 0;
        // Reverses the barcode to be sure each digit will be in the right place
        // regardless the barcode length.
        const code = numericBarcode.split("").reverse();
        // Removes the last barcode digit (should not be took in account for its own computing).
        code.shift();

        // Multiply value of each position by
        // N1  N2  N3  N4  N5  N6  N7  N8  N9  N10 N11 N12 N13 N14 N15 N16 N17 N18
        // x3  X1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  CHECK_DIGIT
        for (let i = 0; i < code.length; i++) {
            if (i % 2 === 0) {
                evensum += parseInt(code[i]);
            } else {
                oddsum += parseInt(code[i]);
            }
        }
        const total = evensum * 3 + oddsum;
        return (10 - (total % 10)) % 10;
    }

    /**
     * Checks if the barcode string is encoded with the provided encoding.
     *
     * Mirrors `odoo.libs.barcode.is_barcode_encoding_valid`, including its reading
     * of a leading zero on a 13-digit code as "this is really a UPC-A" -- the
     * server and the client have to agree on what an EAN-13 is, or the same
     * scan resolves to different products on either side.
     *
     * @param {String} barcode
     * @param {String} encoding could be 'any' (no encoding rules), 'ean8', 'upca' or 'ean13'
     * @returns {boolean}
     */
    check_encoding(barcode, encoding) {
        if (encoding === "any") {
            return true;
        }
        const barcodeSizes = {
            ean8: 8,
            ean13: 13,
            upca: 12,
        };
        return (
            barcode.length === barcodeSizes[encoding] &&
            /^\d+$/.test(barcode) &&
            (encoding !== "ean13" || barcode[0] !== "0") &&
            this.get_barcode_check_digit(barcode) ===
                parseInt(barcode[barcode.length - 1])
        );
    }

    /**
     * Sanitizes a EAN-13 prefix by padding it with chars zero.
     *
     * @param {String} ean
     * @returns {String}
     */
    normalize_ean(ean) {
        ean = ean.substr(0, 13);
        ean = "0".repeat(Math.max(0, 13 - ean.length)) + ean;
        return ean.substr(0, 12) + this.get_barcode_check_digit(ean);
    }

    /**
     * Sanitizes a UPC-A prefix by padding it with chars zero.
     *
     * @param {String} upc
     * @returns {String}
     */
    normalize_upc(upc) {
        return this.normalize_ean("0" + upc).substr(1, 12);
    }

    /**
     * Checks if barcode matches the pattern, and retrieves the optional
     * numerical content encoded in it.
     *
     * @param {String} barcode
     * @param {String} pattern
     * @returns {Object} - value: the numerical value encoded in the barcode (0 if none)
     *                   - base_code: the barcode with the numerical content zeroed out
     *                   - match: boolean
     */
    match_pattern(barcode, pattern) {
        const match = {
            value: 0,
            base_code: barcode,
            match: false,
        };
        if (barcode.length > MAX_BARCODE_LENGTH) {
            return match;
        }

        const numericGroup = pattern.match(NUMERIC_GROUP);
        if (numericGroup) {
            const start = numericGroup.index;
            const wholeSize = numericGroup[1].length;
            const decimalSize = numericGroup[2].length;
            const digits = barcode.substr(start, wholeSize + decimalSize);
            const whole = digits.substr(0, wholeSize);
            const decimal = digits.substr(wholeSize);
            // The slot must hold exactly as many ASCII digits as the pattern declares.
            if (
                digits.length !== wholeSize + decimalSize ||
                !ASCII_DIGITS.test(whole) ||
                !ASCII_DIGITS.test(decimal)
            ) {
                return match;
            }
            match.value =
                parseInt(whole || "0", 10) + (decimal ? parseFloat("0." + decimal) : 0);
            match.base_code =
                barcode.substr(0, start) +
                "0".repeat(wholeSize + decimalSize) +
                barcode.substr(start + wholeSize + decimalSize);
            pattern =
                pattern.substr(0, start) +
                "0".repeat(wholeSize + decimalSize) +
                pattern.substr(start + numericGroup[0].length);
        }

        // `String.match` is unanchored where Python's `re.match` is not.
        // Wrap the whole pattern once instead of splitting on every `|`:
        // splitting cuts through alternation nested inside a group (e.g.
        // "21(a|b)3" -> "^21(a|^b)3"), stitching a stray '^' into the middle
        // of the group and making the second branch unmatchable.
        const anchored = "^(?:" + pattern + ")";
        match.match = Boolean(match.base_code.match(anchored));

        return match;
    }

    /**
     * Attempts to interpret a barcode (string encoding a barcode Code-128)
     *
     * @param {string} barcode
     * @returns {Object|Object[]} for an EPC URI, the list of data objects it
     *      decodes to; otherwise a single object containing:
     *      - code: the barcode
     *      - type: the type of the barcode (e.g. alias, unit product, weighted product...)
     *      - value: if the barcode encodes a numerical value, it will be put there
     *      - base_code: the barcode with all the encoding parts set to zero; the one put on the product in the backend
     */
    parse_barcode(barcode) {
        if (barcode.startsWith("urn:")) {
            return this.parseURI(barcode);
        }
        return this.parseBarcodeNomenclature(barcode);
    }

    parseBarcodeNomenclature(barcode) {
        if (!this.nomenclature) {
            return {
                encoding: "",
                type: "error",
                code: barcode,
                base_code: barcode,
                value: 0,
            };
        }
        // An `alias` rule restates the scan as another barcode, which must then
        // be parsed from the first rule again; `seen` stops a cycle looping.
        const seen = new Set();
        for (;;) {
            const parsedResult = this._matchRules(barcode);
            if (parsedResult.type !== "alias") {
                return parsedResult;
            }
            seen.add(barcode);
            barcode = parsedResult.code;
            if (seen.has(barcode)) {
                parsedResult.type = "error";
                return parsedResult;
            }
        }
    }

    /**
     * Match `barcode` against the nomenclature's rules, once. A matched alias
     * rule yields `type === "alias"` with `code` set to the aliased barcode.
     */
    _matchRules(barcode) {
        const parsedResult = {
            encoding: "",
            type: "error",
            code: barcode,
            base_code: barcode,
            value: 0,
        };
        const conv = this.nomenclature.upc_ean_conv;

        for (const rule of this.nomenclature.rules) {
            let curBarcode = barcode;
            let converted = false;
            // A UPC-A restated as EAN-13 always gains a leading zero, which
            // `check_encoding` reads as "really a UPC-A". So the conversion has
            // to stand in for the encoding check rather than precede it.
            if (
                rule.encoding === "ean13" &&
                ["upc2ean", "always"].includes(conv) &&
                this.check_encoding(barcode, "upca")
            ) {
                curBarcode = "0" + barcode;
                converted = true;
            } else if (
                rule.encoding === "upca" &&
                ["ean2upc", "always"].includes(conv) &&
                barcode[0] === "0" &&
                this.check_encoding(barcode.substr(1), "upca")
            ) {
                curBarcode = barcode.substr(1);
                converted = true;
            }

            if (!converted && !this.check_encoding(barcode, rule.encoding)) {
                continue;
            }

            const match = this.match_pattern(curBarcode, rule.pattern);
            if (!match.match) {
                continue;
            }

            if (rule.type === "alias") {
                parsedResult.type = "alias";
                parsedResult.code = rule.alias;
                return parsedResult;
            }

            parsedResult.encoding = rule.encoding;
            parsedResult.type = rule.type;
            parsedResult.value = match.value;
            parsedResult.code = curBarcode;
            if (rule.encoding === "ean13") {
                parsedResult.base_code = this.normalize_ean(match.base_code);
            } else if (rule.encoding === "upca") {
                parsedResult.base_code = this.normalize_upc(match.base_code);
            } else {
                parsedResult.base_code = match.base_code;
            }
            return parsedResult;
        }
        return parsedResult;
    }

    // URI methods
    /**
     * Parse an URI into a list of objects with either the product and its
     * lot/serial number, either the package.
     *
     * Every branch returns a list -- callers rely on that shape. A URI this
     * method cannot decode is a failed parse, reported as an empty list: the
     * argument is scanned input, so a malformed one is expected traffic.
     *
     * @param {String} barcode
     * @returns {Object[]}
     */
    parseURI(barcode) {
        // urn:<namespace>:<type>:<identifier>:<data>
        const parts = barcode.split(":").map((v) => v.trim());
        if (parts.length !== 5) {
            return [];
        }
        const identifier = parts[3];
        let data = parts[4].split(".");

        const expected = URI_DATA_FIELDS[identifier];
        if (expected === undefined || data.length !== expected) {
            return [];
        }
        if (FILTERED_URI_SCHEMES.includes(identifier)) {
            data = data.slice(1);
        }
        // Only the two leading fields feed the check-digit computation; an
        // SGTIN-198 serial is legitimately alphanumeric and is passed through.
        if (!data.slice(0, 2).every((field) => field && ASCII_DIGITS.test(field))) {
            return [];
        }

        if (identifier.startsWith("sscc")) {
            return this.convertURISSCCDataIntoPackage(barcode, data);
        }
        return this.convertURIGTINDataIntoProductAndTrackingNumber(barcode, data);
    }

    convertURIGTINDataIntoProductAndTrackingNumber(base_code, data) {
        const [gs1CompanyPrefix, itemRefAndIndicator, trackingNumber] = data;
        const indicator = itemRefAndIndicator[0];
        const itemRef = itemRefAndIndicator.slice(1);
        let productBarcode = indicator + gs1CompanyPrefix + itemRef;
        productBarcode += this.get_barcode_check_digit(productBarcode + "0");
        return [
            {
                base_code,
                code: productBarcode,
                encoding: "",
                type: "product",
                value: productBarcode,
            },
            {
                base_code,
                code: trackingNumber,
                encoding: "",
                type: "lot",
                value: trackingNumber,
            },
        ];
    }

    convertURISSCCDataIntoPackage(base_code, data) {
        const [gs1CompanyPrefix, serialReference] = data;
        const extension = serialReference[0];
        const serialRef = serialReference.slice(1);
        let sscc = extension + gs1CompanyPrefix + serialRef;
        sscc += this.get_barcode_check_digit(sscc + "0");
        return [
            {
                base_code,
                code: sscc,
                encoding: "",
                type: "package",
                value: sscc,
            },
        ];
    }
}
