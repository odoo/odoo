odoo.define('barcodes.BarcodeParser', function (require) {
"use strict";

var Class = require('web.Class');
var rpc = require('web.rpc');

const FNC1_CHAR = String.fromCharCode(29);

// The BarcodeParser is used to detect what is the category
// of a barcode (product, partner, ...) and extract an encoded value
// (like weight, price, etc.)
var BarcodeParser = Class.extend({
    init: function(attributes) {
        this.nomenclature_id = attributes.nomenclature_id;
        this.loaded = this.load();
    },

    // This loads the barcode nomenclature and barcode rules which are
    // necessary to parse the barcodes. The BarcodeParser is operational
    // only when those data have been loaded
    load: function(){
        var self = this;
        if (!this.nomenclature_id) {
            return;
        }
        var id = this.nomenclature_id[0];
        return rpc.query({
                model: 'barcode.nomenclature',
                method: 'read',
                args: [[id], ['name', 'rule_ids', 'upc_ean_conv', 'is_gs1_nomenclature', 'gs1_separator_fnc1']],
            }).then(function (nomenclatures){
                self.nomenclature = nomenclatures[0];
                var args = [
                    [['barcode_nomenclature_id', '=', self.nomenclature.id]],
                    ['name', 'sequence', 'type', 'encoding', 'pattern', 'alias', 'gs1_content_type', 'gs1_decimal_usage', 'associated_uom_id'],
                ];
                return rpc.query({
                    model: 'barcode.rule',
                    method: 'search_read',
                    args: args,
                });
            }).then(function(rules){
                rules = rules.sort(function(a, b){ return a.sequence - b.sequence; });
                self.nomenclature.rules = rules;
            });
    },

    // resolves when the barcode parser is operational.
    is_loaded: function() {
        return this.loaded;
    },

    /**
     * This algorithm is identical for all fixed length numeric GS1 data structures.
     *
     * It is also valid for ean8,12(upca),13 check digit, just need to shift with zero to the left to have 18 digit.
     * https://www.gs1.org/sites/default/files/docs/barcodes/GS1_General_Specifications.pdf
     * 
     * @param {String} numericBarcode Need to have a length of 18, and the last numeric char is the check digit (or '0')
     * @returns {number} Check Digit
     */
    get_barcode_check_digit(numericBarcode) {
        var code = numericBarcode.split('');
        if (code.length !== 18) {
            return -1;
        }
    
        // Multiply value of each position by
        // N1  N2  N3  N4  N5  N6  N7  N8  N9  N10 N11 N12 N13 N14 N15 N16 N17 N18
        // x3  X1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  CHECK_DIGIT
        var oddsum = 0, evensum = 0, total = 0;
        code.pop();
        for (var i = 0; i < code.length; i++) {
            if (i % 2 === 0){
                evensum += parseInt(code[i]);
            } else {
                oddsum += parseInt(code[i]);
            }
        }
        total = evensum * 3 + oddsum;
        return ((10 - total % 10) % 10);
    },

    // returns true if the barcode string is encoded with the provided encoding.
    check_encoding: function(barcode, encoding) {
        var len = barcode.length;
        var allnum = /^\d+$/.test(barcode);

        if (encoding === 'ean13') {
            return len === 13 && allnum && this.get_barcode_check_digit("0".repeat(18 - len) + barcode) === parseInt(barcode[len - 1]);
        } else if (encoding === 'ean8') {
            return len === 8 && allnum && this.get_barcode_check_digit("0".repeat(18 - len) + barcode) === parseInt(barcode[len - 1]);
        } else if (encoding === 'upca') {
            return len === 12 && allnum && this.get_barcode_check_digit("0".repeat(18 - len) + barcode) === parseInt(barcode[len - 1]);
        } else if (encoding === 'any') {
            return true;
        } else {
            return false;
        }
    },

    // returns a valid zero padded ean13 from an ean prefix. the ean prefix must be a string.
    sanitize_ean: function(ean){
        ean = ean.substr(0, 13);
        ean = "0".repeat(13 - ean.length) + ean;
        return ean.substr(0, 12) + this.get_barcode_check_digit("0".repeat(5) + ean);
    },

    // Returns a valid zero padded UPC-A from a UPC-A prefix. the UPC-A prefix must be a string.
    sanitize_upc: function(upc) {
        return this.sanitize_ean('0' + upc).substr(1, 12);
    },

    /**
     * Convert YYMMDD GS1 date into a Date object
     * @param {string} gs1Date : YYMMDD string date, length must be 6
     * @returns {Date}
     */
    gs1_date_to_date: function(gs1Date) {

        // Determination of century
        // https://www.gs1.org/sites/default/files/docs/barcodes/GS1_General_Specifications.pdf#page=474&zoom=100,66,113
        var now = new Date();
        var substractYear = parseInt(gs1Date.slice(0, 2)) - (now.getFullYear() % 100);
        var century = Math.floor(now.getFullYear() / 100);
        if ((51 <= substractYear) && (substractYear <= 99)) {
            century--;
        } else if ((-99 <= substractYear) && (substractYear <= -50)) {
            century++;
        }
        var year = century * 100 + parseInt(gs1Date.slice(0, 2));
        
        var date = new Date(year, parseInt(gs1Date.slice(2, 4) - 1));
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
     * @param {Array} match : Result of a regex match with atmost 2 groups (ia and value)
     * @param {Object} rule : Matched Barcode Rule 
     * @returns {Object|null}
     */
    parse_gs1_rule_pattern: function(match, rule) {
        var result = {
            'rule': Object.assign({}, rule),
            'ai': match[1],
            'string_value': match[2]
        };
        if (rule.gs1_content_type === 'measure'){
            var decimalPosition = 0; // Decimal position begin at the end, 0 means no decimal
            if (rule.gs1_decimal_usage){
                decimalPosition = parseInt(match[1][match[1].length - 1]);
            }
            if (decimalPosition > 0) {
                result['value'] = parseFloat(match[2].slice(0, match[2].length - decimalPosition) + "." + match[2].slice(match[2].length - decimalPosition));
            } else {
                result['value'] = parseInt(match[2]);
            }
        } else if (rule.gs1_content_type === 'identifier'){
            if (parseInt(match[2][match[2].length - 1]) !== this.get_barcode_check_digit("0".repeat(18 - match[2].length) + match[2])){
                return null; // Warning ?
            }
            result['value'] = match[2];
        } else if (rule.gs1_content_type === 'date'){
            if (match[2].length !== 6){
                return null; // Warning ?
            }
            result['value'] = this.gs1_date_to_date(match[2]);
        } else {
            result['value'] = match[2];
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
        var self = this;
        var results = [];
        var rules = this.nomenclature.rules.filter((rule) => rule.encoding === 'gs1-128');
        var separatorReg = FNC1_CHAR + "?";
        if (this.nomenclature.gs1_separator_fnc1 && this.nomenclature.gs1_separator_fnc1.trim()){
            separatorReg = `(?:${this.nomenclature.gs1_separator_fnc1})?`;
        }
        function findNextRule(remainingBarcode) {
            for (var i = 0; i < rules.length; i++) {
                var match = remainingBarcode.match("^" + rules[i].pattern + separatorReg);
                if (match && match.length >= 3) {
                    var res = self.parse_gs1_rule_pattern(match, rules[i]);
                    if (res !== null){
                        return {
                            res: res, 
                            remaining_barcode: remainingBarcode.slice(match.index + match[0].length)
                        };
                    }
                }
            }
            return null;
        }

        while (barcode.length > 0) {
            var resBar = findNextRule(barcode);
            // Cannot continue -> Fail to decompose gs1 and return
            if (!resBar || resBar.remaingBarcode === barcode){
                return null;
            }
            barcode = resBar.remaining_barcode;
            results.push(resBar.res);
        }

        return results;
    },

    // Checks if barcode matches the pattern
    // Additionnaly retrieves the optional numerical content in barcode
    // Returns an object containing:
    // - value: the numerical value encoded in the barcode (0 if no value encoded)
    // - base_code: the barcode in which numerical content is replaced by 0's
    // - match: boolean
    match_pattern: function (barcode, pattern, encoding){
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
            match['value'] = parseInt(whole_part) + parseFloat(decimal_part);

            // replace numerical content by 0's in barcode and pattern
            match['base_code'] = barcode.substr(0,num_start);
            var base_pattern = pattern.substr(0,num_start);
            for(var i=0;i<(num_length-2);i++) {
                match['base_code'] += "0";
                base_pattern += "0";
            }
            match['base_code'] += barcode.substr(num_start+num_length-2,barcode.length-1);
            base_pattern += pattern.substr(num_start+num_length,pattern.length-1);

            match['base_code'] = match['base_code']
                .replace("\\\\", "\\")
                .replace("\{", "{")
                .replace("\}","}")
                .replace("\.",".");

            var base_code = match.base_code.split('')
            if (encoding === 'ean13') {
                base_code[12] = '' + this.get_barcode_check_digit("0".repeat(5) + match.base_code);
            } else if (encoding === 'ean8') {
                base_code[7]  = '' + this.get_barcode_check_digit("0".repeat(10) + match.base_code);
            } else if (encoding === 'upca') {
                base_code[11] = '' + this.get_barcode_check_digit("0".repeat(6) + match.base_code);
            }
            match.base_code = base_code.join('')
        }

        if (base_pattern[0] !== '^') {
            base_pattern = "^" + base_pattern;
        }
        match.match = match.base_code.match(base_pattern);

        return match;
    },

    /**
     * Attempts to interpret a barcode (string encoding a barcode Code-128)
     * @param {string} barcode
     * @returns {Object|Array|null} : 
     *  - If nomenclature is GS1 returns a array or null 
     *  - If not, it will return an object containing various information about the barcode:
     *      - code    : the barcode
     *      - type   : the type of the barcode (e.g. alias, unit product, weighted product...)
     *      - value  : if the barcode encodes a numerical value, it will be put there
     *      - base_code : the barcode with all the encoding parts set to zero; the one put on the product in the backend
     */
    parse_barcode: function(barcode){
        var parsed_result = {
            encoding: '',
            type:'error',
            code:barcode,
            base_code: barcode,
            value: 0,
        };

        if (!this.nomenclature) {
            return parsed_result;
        }
        if (this.nomenclature.is_gs1_nomenclature) {
            return this.gs1_decompose_extanded(barcode);
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
                    this.upc_ean_conv in {'ean2upc':'','always':''} ){
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
    },
});

return BarcodeParser;
});
