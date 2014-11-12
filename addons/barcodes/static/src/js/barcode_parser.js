function openerp_barcode_parser(instance,module){

    module.BarcodeParser = instance.web.Class.extend({
        init: function(attributes) {
            var self = this;
            this.nomenclature_id = attributes.nomenclature_id;
            this.load_server_data();
        },

        models: [
        {
            model: 'barcode.nomenclature',
            fields: ['name','rule_ids'],
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

            var rules = self.nomenclature.rules;
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