/** @odoo-module **/

export const FNC1_CHAR = String.fromCharCode(29);
export class BarcodeParserError extends Error {};
import { _t } from "@web/core/l10n/translation";

export class BarcodeParser {
    static barcodeNomenclatureFields = [
        "is_combined",
        "name",
        "rule_ids",
        "separator_expr",
        "upc_ean_conv",
    ];
    static barcodeRuleFields = [
        "alias",
        "encoding",
        "name",
        "pattern",
        "rule_part_ids",
        "sequence",
        "type",
        "associated_uom_id",
    ];
    static BarcodeRulePartsFields = [
        "associated_uom_id",
        "encoding",
        "pattern",
        "rule_id",
        "sequence",
        "type",
    ];
    static async fetchNomenclature(orm, id) {
        // Fetches the nomenclature fields.
        const [nomenclature] = await orm.read(
            "barcode.nomenclature",
            [id],
            this.barcodeNomenclatureFields
        );
        let rules = await orm.searchRead(
            "barcode.rule",
            [["barcode_nomenclature_id", "=", id]],
            this.barcodeRuleFields
        );
        // Fetches the nomenclature's rules.
        rules = rules.sort((a, b) => {
            return a.sequence - b.sequence;
        });
        nomenclature.rules = rules;
        // Fetches the nomenclature rules' groups.
        const groupsIds = new Set();
        for (const rule of nomenclature.rules) {
            rule.rule_part_ids.forEach(partId => groupsIds.add(partId));
        }
        const groups = await orm.searchRead(
            "barcode.rule.part",
            [["id", "in", [...groupsIds]]],
            this.BarcodeRulePartsFields
        );
        // Assigns to each rules their groups.
        for (const rule of nomenclature.rules) {
            rule.groups = rule.rule_part_ids.length
                ? groups.filter(g => rule.rule_part_ids.includes(g.id))
                : [];
        }
        return nomenclature;
    }

    constructor() {
        this.setup(...arguments);
    }

    setup({ nomenclatures }) {
        this.nomenclatures = nomenclatures;
        this.useCombinedNomenclatures = Boolean(this.nomenclatures.find(nom => nom.is_combined))
    }

    /**
     * This algorithm is identical for all fixed length numeric GS1 data structures.
     *
     * It is also valid for EAN-8, EAN-12 (UPC-A), EAN-13 check digit after sanitizing.
     * https://www.gs1.org/sites/default/files/docs/barcodes/GS1_General_Specifications.pdf
     *
     * @param {String} numericBarcode Need to have a length of 18
     * @returns {number} Check Digit
     */
    get_barcode_check_digit(numericBarcode) {
        let oddsum = 0, evensum = 0, total = 0;
        // Reverses the barcode to be sure each digit will be in the right place
        // regardless the barcode length.
        const code = numericBarcode.split('').reverse();
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
        total = evensum * 3 + oddsum;
        return (10 - total % 10) % 10;
    }

    /**
     * Checks if the barcode string is encoded with the provided encoding.
     *
     * @param {String} barcode
     * @param {String} encoding could be 'any' (no encoding rules), 'ean8', 'upca' or 'ean13'
     * @returns {boolean}
     */
    check_encoding(barcode, encoding) {
        if (encoding === 'any') {
            return true;
        }
        const barcodeSizes = {
            ean8: 8,
            ean13: 13,
            upca: 12,
        };
        return barcode.length === barcodeSizes[encoding] && /^\d+$/.test(barcode) &&
            this.get_barcode_check_digit(barcode) === parseInt(barcode[barcode.length - 1]);
    }

    /**
     * Sanitizes a EAN-13 prefix by padding it with chars zero.
     *
     * @param {String} ean
     * @returns {String}
     */
    sanitize_ean(ean) {
        ean = ean.substr(0, 13);
        ean = "0".repeat(13 - ean.length) + ean;
        return ean.substr(0, 12) + this.get_barcode_check_digit(ean);
    }

    /**
     * Sanitizes a UPC-A prefix by padding it with chars zero.
     *
     * @param {String} upc
     * @returns {String}
     */
    sanitize_upc(upc) {
        return this.sanitize_ean(upc).substr(1, 12);
    }

    // Checks if barcode matches the pattern
    // Additionnaly retrieves the optional numerical content in barcode
    // Returns an object containing:
    // - value: the numerical value encoded in the barcode (0 if no value encoded)
    // - base_code: the barcode in which numerical content is replaced by 0's
    // - match: boolean
    match_pattern(barcode, pattern, encoding) {
        var match = {
            value: 0,
            base_code: barcode,
            match: false,
        };
        barcode = barcode.replace("\\", "\\\\").replace("{", '\{').replace("}", "\}").replace(".", "\.");

        var numerical_content = pattern.match(/[{][N]*[D]*[}]/); // look for numerical content in pattern
        var base_pattern = pattern;
        if(numerical_content){ // the pattern encodes a numerical content
            var num_start = numerical_content.index; // start index of numerical content
            var num_length = numerical_content[0].length; // length of numerical content
            var value_string = barcode.substr(num_start, num_length-2); // numerical content in barcode
            var whole_part_match = numerical_content[0].match("[{][N]*[D}]"); // looks for whole part of numerical content
            var decimal_part_match = numerical_content[0].match("[{N][D]*[}]"); // looks for decimal part
            var whole_part = value_string.substr(0, whole_part_match.index+whole_part_match[0].length-2); // retrieve whole part of numerical content in barcode
            var decimal_part = "0." + value_string.substr(decimal_part_match.index, decimal_part_match[0].length-1); // retrieve decimal part
            if (whole_part === ''){
                whole_part = '0';
            }
            match.value = parseInt(whole_part) + parseFloat(decimal_part);

            // replace numerical content by 0's in barcode and pattern
            match.base_code = barcode.substr(0, num_start);
            base_pattern = pattern.substr(0, num_start);
            for(var i=0;i<(num_length-2);i++) {
                match.base_code += "0";
                base_pattern += "0";
            }
            match.base_code += barcode.substr(num_start + num_length - 2, barcode.length - 1);
            base_pattern += pattern.substr(num_start + num_length, pattern.length - 1);

            match.base_code = match.base_code
                .replace("\\\\", "\\")
                .replace("\{", "{")
                .replace("\}","}")
                .replace("\.",".");

            var base_code = match.base_code.split('');
            if (encoding === 'ean13') {
                base_code[12] = '' + this.get_barcode_check_digit(match.base_code);
            } else if (encoding === 'ean8') {
                base_code[7]  = '' + this.get_barcode_check_digit(match.base_code);
            } else if (encoding === 'upca') {
                base_code[11] = '' + this.get_barcode_check_digit(match.base_code);
            }
            match.base_code = base_code.join('');
        }

        base_pattern = base_pattern.split('|')
            .map(part => part.startsWith('^') ? part : '^' + part)
            .join('|');
        match.match = match.base_code.match(base_pattern);

        return match;
    }

    /**
     * Attempts to interpret a barcode (string encoding a barcode Code-128)
     *
     * @param {string} barcode
     * @returns {Object} the returned object containing informations about the barcode:
     *      - code: the barcode
     *      - type: the type of the barcode (e.g. alias, unit product, weighted product...)
     *      - value: if the barcode encodes a numerical value, it will be put there
     *      - base_code: the barcode with all the encoding parts set to zero; the one put on the product in the backend
     */
    parse_barcode(barcode) {
        for (const nomenclature of this.nomenclatures) {
            const parsedData = this._parse_combined_barcode(barcode, nomenclature);
            if (parsedData) {
                return parsedData;
            }
        }
        throw new BarcodeParserError(_t("This barcode can't be partially or fully parsed."));
    }

    _parse_barcode(barcode) {
        var parsed_result = {
            encoding: '',
            type:'error',
            code: barcode,
            base_code: barcode,
            value: 0,
        };

        if (!this.nomenclatures) {
            return parsed_result;
        }

        var rules = this.nomenclature.rules;
        for (var i = 0; i < rules.length; i++) {
            var rule = rules[i];
            var cur_barcode = barcode;

            if (    rule.encoding === 'ean13' &&
                    this.check_encoding(barcode,'upca') &&
                    this.nomenclature.upc_ean_conv in {'upc2ean':'','always':''} ){
                cur_barcode = '0' + cur_barcode;
            } else if (rule.encoding === 'upca' &&
                    this.check_encoding(barcode,'ean13') &&
                    barcode[0] === '0' &&
                    this.nomenclature.upc_ean_conv in {'ean2upc':'','always':''} ){
                cur_barcode = cur_barcode.substr(1,12);
            }

            if (!this.check_encoding(cur_barcode,rule.encoding)) {
                continue;
            }

            var match = this.match_pattern(cur_barcode, rules[i].pattern, rule.encoding);
            if (match.match) {
                if(rules[i].type === 'alias') {
                    barcode = rules[i].alias;
                    parsed_result.code = barcode;
                    parsed_result.type = 'alias';
                }
                else {
                    parsed_result.encoding  = rules[i].encoding;
                    parsed_result.type      = rules[i].type;
                    parsed_result.value     = match.value;
                    parsed_result.code      = cur_barcode;
                    if (rules[i].encoding === "ean13"){
                        parsed_result.base_code = this.sanitize_ean(match.base_code);
                    }
                    else{
                        parsed_result.base_code = match.base_code;
                    }
                    return parsed_result;
                }
            }
        }
        return parsed_result;
    }

    /**
     * Try to decompose the extanded barcode into several unit of information using nomenclature rules
     *
     * @param {string} barcode
     * @param {Object} nomenclature
     * @returns {Boolean|Array} Array of object if nomenclature was able to
     *                          parse the barcode, false otherwise.
     */
    _parse_combined_barcode(barcode, nomenclature) {
        const results = [];
        const {rules} = nomenclature;
        barcode = this._convertGS1Separators(barcode, nomenclature);
        // For combined nomenclature, we add the separator in the regex to split
        // the barcode once a rule is matched. For not combined nomenclature,
        // the barcode has to completely match a single rule.
        const regexEnd = nomenclature.combined ? `(?:${FNC1_CHAR}+)?` : "$";

        while (barcode.length > 0) {
            const barcodeLength = barcode.length;
            for (const rule of rules) {
                const match = barcode.match(`^${rule.pattern}${regexEnd}`);
                if (match && match.length >= 2) {
                    const res = this.parse_rule_pattern(match, rule);
                    if (res) {
                        barcode = barcode.slice(match.index + match[0].length);
                        results.push(...res);
                        if (barcode.length === 0) {
                            return results; // Barcode completly parsed, no need to keep looping.
                        }
                    }
                }
            }
            if (barcodeLength === barcode.length) {
                return false; // This barcode can't be partially or fully parsed.
            }
        }

        return results;
    }

    /**
     * Convert YYMMDD GS1 date into a Date object
     *
     * @param {string} gs1Date YYMMDD string date, length must be 6
     * @returns {Date}
     */
    gs1_date_to_date(gs1Date) {
        // See 7.12 Determination of century in dates:
        // https://www.gs1.org/sites/default/files/docs/barcodes/GS1_General_Specifications.pdfDetermination of century
        const now = new Date();
        const substractYear = parseInt(gs1Date.slice(0, 2)) - (now.getFullYear() % 100);
        let century = Math.floor(now.getFullYear() / 100);
        if (51 <= substractYear && substractYear <= 99) {
            century--;
        } else if (-99 <= substractYear && substractYear <= -50) {
            century++;
        }
        const year = century * 100 + parseInt(gs1Date.slice(0, 2));
        const date = new Date(year, parseInt(gs1Date.slice(2, 4) - 1));

        if (gs1Date.slice(-2) === '00'){
            // Day is not mandatory, when not set -> last day of the month
            date.setDate(new Date(year, parseInt(gs1Date.slice(2, 4)), 0).getDate());
        } else {
            date.setDate(parseInt(gs1Date.slice(-2)));
        }
        return date;
    }

    /**
     * Perform interpretation of the barcode value depending of the rule.gs1_content_type
     *
     * @param {Array} match Result of a regex match with atmost 2 groups (ia and value)
     * @param {Object} rule Matched Barcode Rule
     * @returns {Object|null}
     */
    parse_rule_pattern(match, rule) {
        let decimalPosition = 0;
        const results = [];
        if (!this.check_encoding(match[0], rule.encoding)) {
            // The rule expects a specific encoding and the barcode doesn't respect it.
            return false;
        }
        // Defines result part's data for each match/rule group pair.
        for (let i = 0; i < rule.groups.length; i++) {
            const value = match[i + 1];
            const group = rule.groups[i];
            if (!this.check_encoding(value, group.encoding)) {
                // The rule part expects a specific encoding and the barcode doesn't respect it.
                return false;
            }
            const result = {
                rule: Object.assign({}, rule),
                group: Object.assign({}, group),
                string_value: value,
                code: value,
                value,
                base_code: match[0],
                type: group.type
            };

            if (group.type === "decimal_position") {
                result.value = parseInt(value);
                decimalPosition = result.value;
            } else if (group.type === "measure") {
                decimalPosition = decimalPosition || group.decimal_position;
                if (decimalPosition > 0) {
                    const integral = value.slice(0, value.length - decimalPosition);
                    const decimal = value.slice(value.length - decimalPosition);
                    result.value = parseFloat( integral + "." + decimal);
                } else {
                    result.value = parseInt(value);
                }
            } else if (group.type === "date") {
                if (value.length !== 6) {
                    // TODO: Adapt to more format then only YYMMDD.
                    throw new Error(_t("Invalid barcode: can't be formated as date"));
                }
                result.value = this.gs1_date_to_date(value);
            } else if (group.type === "product") {
                if (rule.encoding === "ean13") {
                    result.value = this.sanitize_ean(value.padEnd(13, "0"));
                } else if (rule.encoding === "any" && group.encoding === "ean13") {
                    result.value = this.sanitize_ean(value);
                }
            }
            results.push(result);
        }
        return results
    }

    /**
     * The FNC1 is the default GS1 separator character, but through the field `separator_expr`,
     * the user has the possibility to define one or multiple characters to use as separator as
     * a regex. This method replaces all of the matches in the given barcode by the FNC1.
     *
     * @param {string} barcode
     * @returns {string}
     */
    _convertGS1Separators(barcode, nomenclature) {
        if (nomenclature.is_combined) {
            barcode = barcode.replace(nomenclature.separator_expr, FNC1_CHAR);
        }
        return barcode;
    }
}
