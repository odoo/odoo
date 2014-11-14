openerp.barcodes = function(instance) {
    "use strict";

    instance.barcodes = {};
    var module = instance.barcodes;

    module.BarcodeParser = instance.web.Class.extend({
        init: function(attributes) {
            var self = this;
            this.nomenclature_id = attributes.nomenclature_id;
            this.loaded = this.load_server_data();
        },

        is_loaded: function() {
            return self.loaded;
        },

        models: [
        {
            model: 'barcode.nomenclature',
            fields: ['name','rule_ids', 'strict_ean'],
            domain: function(self){ return [] },
            loaded: function(self,nomenclatures){
                if (self.nomenclature_id) {
                    for (var i = 0; i < nomenclatures.length; i++) {
                        if (nomenclatures[i].id === self.nomenclature_id[0]) {
                            self.nomenclature = nomenclatures[i];
                        }
                    }
                }
                self.nomenclature = self.nomenclature || null;
            },
        }, {
            model: 'barcode.rule',
            fields: ['name','sequence','type','encoding','pattern','alias'],
            domain: function(self){ return [['barcode_nomenclature_id','=',self.nomenclature ? self.nomenclature.id : 0]]; },
            loaded: function(self,rules){
                if (self.nomenclature) {
                    rules = rules.sort(function(a,b){ return a.sequence - b.sequence; });
                    self.nomenclature.rules = rules;
                }
            },
        },
        ],

        // loads all the needed data on the sever. returns a deferred indicating when all the data has loaded. 
        load_server_data: function(){
            var self = this;
            var loaded = new $.Deferred();
            var progress = 0;
            var progress_step = 1.0 / self.models.length;
            var tmp = {}; // this is used to share a temporary state between models loaders

            function load_model(index){
                if(index >= self.models.length){
                    loaded.resolve();
                }else{
                    var model = self.models[index];
                    //self.pos_widget.loading_message(_t('Loading')+' '+(model.label || model.model || ''), progress);

                    var cond = typeof model.condition === 'function'  ? model.condition(self,tmp) : true;
                    if (!cond) {
                        load_model(index+1);
                        return;
                    }

                    var fields =  typeof model.fields === 'function'  ? model.fields(self,tmp)  : model.fields;
                    var domain =  typeof model.domain === 'function'  ? model.domain(self,tmp)  : model.domain;
                    var context = typeof model.context === 'function' ? model.context(self,tmp) : model.context; 
                    progress += progress_step;
                    
                    if( model.model ){
                        new instance.web.Model(model.model).query(fields).filter(domain).context(context).all()
                            .then(function(result){
                                try{    // catching exceptions in model.loaded(...)
                                    $.when(model.loaded(self,result,tmp))
                                        .then(function(){ load_model(index + 1); },
                                              function(err){ loaded.reject(err); });
                                }catch(err){
                                    console.error(err.stack);
                                    loaded.reject(err);
                                }
                            },function(err){
                                loaded.reject(err);
                            });
                    }else if( model.loaded ){
                        try{    // catching exceptions in model.loaded(...)
                            $.when(model.loaded(self,tmp))
                                .then(  function(){ load_model(index +1); },
                                        function(err){ loaded.reject(err); });
                        }catch(err){
                            loaded.reject(err);
                        }
                    }else{
                        load_model(index + 1);
                    }
                }
            }

            try{
                load_model(0);
            }catch(err){
                loaded.reject(err);
            }
            return loaded;
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

            function match_pattern(barcode, pattern){
                var match = {
                    value: 0,
                    base_code: barcode,
                    match: false,
                };
                barcode = barcode.replace("\\", "\\\\").replace("{", '\{').replace("}", "\}").replace(".", "\.");

                var numerical_content = pattern.match(/[{][N]*[D]*[}]/);
                var base_pattern = pattern;
                if(numerical_content){
                    var num_start = numerical_content.index;
                    var num_length = numerical_content[0].length;
                    var value_string = barcode.substr(num_start, num_length-2);
                    var whole_part_match = numerical_content[0].match("[{][N]*[D}]");
                    var decimal_part_match = numerical_content[0].match("[{N][D]*[}]");
                    var whole_part = value_string.substr(0, whole_part_match.index+whole_part_match[0].length-2);
                    var decimal_part = "0." + value_string.substr(decimal_part_match.index, decimal_part_match[0].length-1);
                    if (whole_part === ''){
                        whole_part = '0';
                    }
                    match['value'] = parseInt(whole_part) + parseFloat(decimal_part);
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