odoo.define('barcodes.BarcodeParser', function (require) {
"use strict";

var Class = require('web.Class');
var rpc = require('web.rpc');

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
                args: [[id], ['name','rule_ids','upc_ean_conv']],
            })
            .then(function (nomenclatures){
                self.nomenclature = nomenclatures[0];

                var args = [
                    [['barcode_nomenclature_id', '=', self.nomenclature.id]],
                    ['name', 'sequence', 'type', 'encoding', 'pattern', 'alias'],
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

    // attempts to interpret a barcode (string encoding a barcode Code-128)
    // it will return an object containing various information about the barcode.
    // most importantly :
    // - code    : the barcode
    // - type   : the type of the barcode (e.g. alias, unit product, weighted product...)
    //
    // - value  : if the barcode encodes a numerical value, it will be put there
    // - base_code : the barcode with all the encoding parts set to zero; the one put on
    //               the product in the backend
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
