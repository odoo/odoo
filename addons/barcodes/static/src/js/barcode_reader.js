function openerp_barcode_reader(instance,module){

    module.BarcodeReader = instance.web.Class.extend({
 
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
        parse_barcode: function(barcode, nomenclature){
            var self = this;
            var parsed_result = {
                encoding: '',
                type:'error',  
                code:barcode,
                base_code: barcode,
                value: 0,
            };
            
            if (!nomenclature) {
                return parsed_result;
            }

            function match_pattern(barcode,pattern){
                if(barcode.length < pattern.replace(/[{}]/g, '').length){
                    return false; // Match of this pattern is impossible
                }
                var numerical_content = false; // Used to detect when we are between { }
                for(var i = 0, j = 0; i < pattern.length; i++, j++){
                    var p = pattern[i];
                    if(p === "{" || p === "}"){
                        numerical_content = !numerical_content;
                        j--;
                        continue;
                    }
                    
                    if(!numerical_content && p !== '*' && p !== barcode[j]){
                        return false;
                    }
                }
                return true;
            }
            
            function get_value(barcode,pattern){
                var value = 0;
                var decimals = 0;
                var numerical_content = false;
                for(var i = 0, j = 0; i < pattern.length; i++, j++){
                    var p = pattern[i];
                    if(!numerical_content && p !== "{"){
                        continue;
                    }
                    else if(p === "{"){
                        numerical_content = true;
                        j--;
                        continue;
                    }
                    else if(p === "}"){
                        break;
                    }

                    var v = parseInt(barcode[j]);
                    if(p === 'N'){
                        value *= 10;
                        value += v;
                    }else if(p === 'D'){   // FIXME precision ....
                        decimals += 1;
                        value += v * Math.pow(10,-decimals);
                    }
                }
                return value;
            }

            function get_basecode(barcode,pattern,encoding){
                var base = '';
                var numerical_content = false;
                for(var i = 0, j = 0; i < pattern.length; i++, j++){
                    var p = pattern[i];
                    if(p === "{" || p === "}"){
                        numerical_content = !numerical_content;
                        j--;
                        continue;
                    }

                    if(numerical_content){
                        base += '0';
                    }
                    else{
                        base += barcode[j];
                    }
                }
                for(i=j; i<barcode.length; i++){ // Read the rest of the barcode
                    base += barcode[i];
                }
                if(encoding === "ean13"){
                    base = self.sanitize_ean(base);
                }
                return base;
            }

            var rules = nomenclature.rules;
            for (var i = 0; i < rules.length; i++) {
                if (match_pattern(barcode,rules[i].pattern)) {
                    if(rules[i].type === 'alias') {
                        barcode = rules[i].alias;
                        parsed_result.code = barcode;
                        parsed_result.type = 'alias';
                    }
                    else {
                        parsed_result.encoding  = rules[i].encoding;
                        parsed_result.type      = rules[i].type;
                        parsed_result.value     = get_value(barcode,rules[i].pattern);
                        parsed_result.base_code = get_basecode(barcode,rules[i].pattern,parsed_result.encoding);
                        return parsed_result;
                    }
                }
            }
            return parsed_result;
        },
    });
}