odoo.define('barcodes_gs1_nomenclature/static/src/js/barcode_parser.js', function (require) {
"use strict";

const BarcodeParser = require('barcodes.BarcodeParser');
const FNC1_CHAR = String.fromCharCode(29);
const {_lt} = require('web.core');
class GS1BarcodeError extends Error {};

BarcodeParser.include({
    /**
     * Convert YYMMDD GS1 date into a Date object
     *
     * @param {string} gs1Date YYMMDD string date, length must be 6
     * @returns {Date}
     */
    gs1_date_to_date: function(gs1Date) {
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
    },

    /**
     * Perform interpretation of the barcode value depending ot the rule.gs1_content_type
     *
     * @param {Array} match Result of a regex match with atmost 2 groups (ia and value)
     * @param {Object} rule Matched Barcode Rule
     * @returns {Object|null}
     */
    parse_gs1_rule_pattern: function(match, rule) {
        const result = {
            rule: Object.assign({}, rule),
            ai: match[1],
            string_value: match[2],
            code: match[2],
            base_code: match[2],
            type: rule.type
        };
        if (rule.gs1_content_type === 'measure'){
            let decimalPosition = 0; // Decimal position begin at the end, 0 means no decimal
            if (rule.gs1_decimal_usage){
                decimalPosition = parseInt(match[1][match[1].length - 1]);
            }
            if (decimalPosition > 0) {
                const integral = match[2].slice(0, match[2].length - decimalPosition);
                const decimal = match[2].slice(match[2].length - decimalPosition);
                result.value = parseFloat( integral + "." + decimal);
            } else {
                result.value = parseInt(match[2]);
            }
        } else if (rule.gs1_content_type === 'identifier'){
            if (parseInt(match[2][match[2].length - 1]) !== this.get_barcode_check_digit("0".repeat(18 - match[2].length) + match[2])){
                throw new Error(_lt("Invalid barcode: the check digit is incorrect"));
                // return {error: _lt("Invalid barcode: the check digit is incorrect")};
            }
            result.value = match[2];
        } else if (rule.gs1_content_type === 'date'){
            if (match[2].length !== 6){
                throw new Error(_lt("Invalid barcode: can't be formated as date"));
                // return {error: _lt("Invalid barcode: can't be formated as date")};
            }
            result.value = this.gs1_date_to_date(match[2]);
        } else {
            result.value = match[2];
        }
        return result;
    },

    /**
     * Try to decompose the gs1 extanded barcode into several unit of information using gs1 rules.
     *
     * @param {string} barcode
     * @returns {Array} Array of object
     */
    gs1_decompose_extanded: function(barcode) {
        const results = [];
        const rules = this.nomenclature.rules.filter(rule => rule.encoding === 'gs1-128');
        const separatorReg = FNC1_CHAR + "?";

        while (barcode.length > 0) {
            const barcodeLength = barcode.length;
            for (const rule of rules) {
                const match = barcode.match("^" + rule.pattern + separatorReg);
                if (match && match.length >= 3) {
                    const res = this.parse_gs1_rule_pattern(match, rule);
                    if (res) {
                        barcode = barcode.slice(match.index + match[0].length);
                        results.push(res);
                        if (barcode.length === 0) {
                            return results; // Barcode completly parsed, no need to keep looping.
                        }
                    } else {
                        throw new GS1BarcodeError(_lt("This barcode can't be parsed by any barcode rules."));
                    }
                }
            }
            if (barcodeLength === barcode.length) {
                throw new GS1BarcodeError(_lt("This barcode can't be partially or fully parsed."));
            }
        }

        return results;
    },

    /**
     * @override
     * @returns {Object|Array|null} If nomenclature is GS1, returns an array or null
     */
    parse_barcode: function(barcode){
        if (this.nomenclature && this.nomenclature.is_gs1_nomenclature) {
            return this.gs1_decompose_extanded(barcode);
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _barcodeNomenclatureFields: function () {
        const fieldNames = this._super(...arguments);
        fieldNames.push('is_gs1_nomenclature', 'gs1_separator_fnc1');
        return fieldNames;
    },

    /**
     * @override
     */
    _barcodeRuleFields: function () {
        const fieldNames = this._super(...arguments);
        fieldNames.push('gs1_content_type', 'gs1_decimal_usage', 'associated_uom_id');
        return fieldNames;
    },
});

return {
    BarcodeParser,
    FNC1_CHAR,
    GS1BarcodeError
};
});
