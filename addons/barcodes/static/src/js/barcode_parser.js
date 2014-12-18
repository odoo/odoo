openerp.barcodes = function(instance) {
    "use strict";

    instance.barcodes = {};
    var module = instance.barcodes;

    // The BarcodeParser is used to detect what is the category
    // of a barcode (product, partner, ...) and extract an encoded value
    // (like weight, price, etc.)
    module.BarcodeParser = instance.web.Class.extend({
        init: function(attributes) {
            var self = this;
            this.nomenclature_id = attributes.nomenclature_id;
            this.loaded = this.load();
        },

        // This loads the barcode nomenclature and barcode rules which are
        // necessary to parse the barcodes. The BarcodeParser is operational
        // only when those data have been loaded
        load: function(){
            var self = this;
            return new instance.web.Model('barcode.nomenclature')
                .query(['name','rule_ids','strict_ean'])
                .filter([['id','=',this.nomenclature_id[0]]])
                .first()
                .then(function(nomenclature){
                    self.nomenclature = nomenclature;

                    return new instance.web.Model('barcode.rule')
                        .query(['name','sequence','type','encoding','pattern','alias'])
                        .filter([['barcode_nomenclature_id','=',self.nomenclature.id ]])
                        .all()
                }).then(function(rules){
                    rules = rules.sort(function(a,b){ return a.sequence - b.sequence; });
                    self.nomenclature.rules = rules;
                });
        },

        // resolves when the barcode parser is operational.
        is_loaded: function() {
            return self.loaded;
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
                if(i % 2 == 0){
                    oddsum += Number(code[i]);
                }else{
                    evensum += Number(code[i]);
                }
            }
            total = oddsum * 3 + evensum;
            return Number((10 - total % 10) % 10);
        },

        // returns true if the ean is a valid EAN barcode number by checking the control digit.
        // ean must be a string
        check_ean: function(ean){
            return /^\d+$/.test(ean) && this.ean_checksum(ean) === Number(ean[ean.length-1]);
        },

        // returns a valid zero padded ean13 from an ean prefix. the ean prefix must be a string.
        sanitize_ean: function(ean){
            ean = ean.substr(0,13);

            for(var n = 0, count = (13 - ean.length); n < count; n++){
                ean = ean + '0';
            }
            return ean.substr(0,12) + this.ean_checksum(ean);
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
            var self = this;
            var parsed_result = {
                encoding: '',
                type:'error',  
                code:barcode,
                base_code: barcode,
                value: 0,
            };
            if (!self.nomenclature) {
                return parsed_result;
            }

            // Checks if barcode matches the pattern
            // Additionnaly retrieves the optional numerical content in barcode
            // Returns an object containing:
            // - value: the numerical value encoded in the barcode (0 if no value encoded)
            // - base_code: the barcode in which numerical content is replaced by 0's
            // - match: boolean
            function match_pattern(barcode, pattern){
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
                    
                    match['base_code'] = match['base_code'].replace("\\\\", "\\").replace("\{", "{").replace("\}","}").replace("\.",".");
                }

                match['match'] = match['base_code'].substr(0,base_pattern.length).match(base_pattern);
                return match;
            }

            // If the nomenclature does not use strict EAN, prepend the barcode with a 0 if it seems
            // that it has been striped by the barcode scanner, when trying to match an EAN13 rule
            var prepend_zero = false;
            if(!self.strict_ean && barcode.length === 12 && self.check_ean("0"+barcode)){
                prepend_zero = true;
            }
            var rules = self.nomenclature.rules;
            for (var i = 0; i < rules.length; i++) {
                var cur_barcode = barcode;
                if (prepend_zero && rules[i].encoding == 'ean13'){
                    cur_barcode = '0'+cur_barcode;
                }
                var match = match_pattern(cur_barcode,rules[i].pattern);
                if (match.match) {
                    if(rules[i].type === 'alias') {
                        barcode = rules[i].alias;
                        parsed_result.code = barcode;
                        parsed_result.type = 'alias';
                    }
                    else {
                        parsed_result.encoding  = rules[i].encoding;
                        parsed_result.type      = rules[i].type;
                        parsed_result.value     = match.value
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
}
