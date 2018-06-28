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
        rpc.query({
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

    // returns the checksum of the ean13, or -1 if the ean has not the correct length, ean must be a string
    ean_checksum: function(ean){
        var code = ean.split('');
        if(code.length !== 13){
            return -1;
        }
        var oddsum = 0, evensum = 0, total = 0;
        code = code.reverse().splice(1);
        for(var i = 0; i < code.length; i++){
            if(i % 2 === 0){
                oddsum += Number(code[i]);
            }else{
                evensum += Number(code[i]);
            }
        }
        total = oddsum * 3 + evensum;
        return Number((10 - total % 10) % 10);
    },

    // returns the checksum of the ean8, or -1 if the ean has not the correct length, ean must be a string
    ean8_checksum: function(ean){
        var code = ean.split('');
        if (code.length !== 8) {
            return -1;
        }
        var sum1  = Number(code[1]) + Number(code[3]) + Number(code[5]);
        var sum2  = Number(code[0]) + Number(code[2]) + Number(code[4]) + Number(code[6]);
        var total = sum1 + 3 * sum2;
        return Number((10 - total % 10) % 10);
    },
    

    // returns true if the ean is a valid EAN barcode number by checking the control digit.
    // ean must be a string
    check_ean: function(ean){
        return /^\d+$/.test(ean) && this.ean_checksum(ean) === Number(ean[ean.length-1]);
    },

    // returns true if the barcode string is encoded with the provided encoding.
    check_encoding: function(barcode, encoding) {
        var len    = barcode.length;
        var allnum = /^\d+$/.test(barcode);
        var check  = Number(barcode[len-1]);

        if (encoding === 'ean13') {
            return len === 13 && allnum && this.ean_checksum(barcode) === check;
        } else if (encoding === 'ean8') {
            return len === 8  && allnum && this.ean8_checksum(barcode) === check;
        } else if (encoding === 'upca') {
            return len === 12 && allnum && this.ean_checksum('0'+barcode) === check;
        } else if (encoding === 'any') {
            return true;
        } else {
            return false;
        }
    },

    // returns a valid zero padded ean13 from an ean prefix. the ean prefix must be a string.
    sanitize_ean: function(ean){
        ean = ean.substr(0,13);

        for(var n = 0, count = (13 - ean.length); n < count; n++){
            ean = '0' + ean;
        }
        return ean.substr(0,12) + this.ean_checksum(ean);
    },

    // Returns a valid zero padded UPC-A from a UPC-A prefix. the UPC-A prefix must be a string.
    sanitize_upc: function(upc) {
        return this.sanitize_ean('0'+upc).substr(1,12);
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
                base_code[12] = '' + this.ean_checksum(match.base_code);
            } else if (encoding === 'ean8') {
                base_code[7]  = '' + this.ean8_checksum(match.base_code);
            } else if (encoding === 'upca') {
                base_code[11] = '' + this.ean_checksum('0' + match.base_code);
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
