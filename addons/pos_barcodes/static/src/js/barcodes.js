openerp.pos_barcodes = function(instance){
    var module = instance.point_of_sale;
    var _t     = instance.web._t;

    // At POS Startup, load the barcode nomenclature and add it to the pos model
    module.PosModel.prototype.models.push({
        model: 'barcode.nomenclature',
        fields: ['name','rule_ids'],
        domain: function(self){ return [] },
        loaded: function(self,nomenclatures){
            if (self.config.barcode_nomenclature_id) {
                for (var i = 0; i < nomenclatures.length; i++) {
                    if (nomenclatures[i].id === self.config.barcode_nomenclature_id[0]) {
                        self.nomenclature = nomenclatures[i];
                    }
                }
            }
            self.nomenclature = self.nomenclature || null;
        },
    });

    module.PosModel.prototype.models.push({
        model: 'barcode.rule',
        fields: ['name','priority','type','pattern'],
        domain: function(self){ return [['barcode_nomenclature_id','=',self.nomenclature ? self.nomenclature.id : 0]]; },
        loaded: function(self,rules){
            if (self.nomenclature) {
                rules = rules.sort(function(a,b){ return b.priority - a.priority; });
                self.nomenclature.rules = rules;
                for (var i = 0; i < rules.length; i++) {
                    var pattern = rules[i].pattern;
                    pattern = pattern.replace(/[x\*]/gi,'x');
                    
                    while (pattern.length < 12) {
                        pattern += 'x';
                    }
                 
                    rules[i].pattern = pattern;
                }
            }
        },
    });

    module.BarcodeReader.include({
        parse_ean: function(ean) {
            var self = this;
            var parse_result = {
                encoding: 'ean13',
                type: 'error',
                code: ean,
                base_code: ean,
                value: 0,
            };

            if (!this.pos.nomenclature) {
                return this._super(ean);
            }

            if (!this.check_ean(ean)) {
                return parse_result;
            }

            function is_number(char) {
                n = char.charCodeAt(0);
                return n >= 48 && n <= 57;
            }

            function match_pattern(ean,pattern) {
                for (var i = 0; i < pattern.length; i++) {
                    var p = pattern[i];
                    var e = ean[i];
                    if( is_number(p) && p !== e ){
                        return false;
                    }
                }
                return true;
            }

            function get_value(ean,pattern){
                var value = 0;
                var decimals = 0;
                for(var i = 0; i < pattern.length; i++){
                    var p = pattern[i];
                    var v = parseInt(ean[i]);
                    if( p === 'N'){
                        value *= 10;
                        value += v;
                    }else if( p === 'D'){   // FIXME precision ...
                        decimals += 1;
                        value += v * Math.pow(10,-decimals);
                    }
                }
                return value;
            }

            function get_basecode(ean,pattern){
                var base = '';
                for(var i = 0; i < pattern.length; i++){
                    var p = pattern[i];
                    var v = ean[i];
                    if( p === 'x'  || is_number(p)){
                        base += v;
                    }else{
                        base += '0';
                    }
                }
                return self.sanitize_ean(base);
            }

            var rules = this.pos.nomenclature.rules;

            for (var i = 0; i < rules.length; i++) {
                if (match_pattern(ean,rules[i].pattern)) {
                    parse_result.type      = rules[i].type;
                    parse_result.value     = get_value(ean,rules[i].pattern);
                    parse_result.base_code = get_basecode(ean,rules[i].pattern);
                    return parse_result;
                }
            }

            return parse_result;
        },
    });

};
