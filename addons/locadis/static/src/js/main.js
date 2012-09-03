openerp.locadis = function(instance){

    var module = instance.point_of_sale;
    var QWeb = instance.web.qweb;

    console.log('PosModel?', module.PosModel);

    module.PosModel = module.PosModel.extend({
        // all this copy paste just to load the product.dont_vidange field ... :(
        load_server_data: function(){
            console.log('loading');
            var self = this;

            var loaded = self.fetch('res.users',['name','company_id'],[['id','=',this.session.uid]]) 
                .pipe(function(users){
                    self.set('user',users[0]);

                    return self.fetch('res.company',
                    [
                        'currency_id',
                        'email',
                        'website',
                        'company_registry',
                        'vat',
                        'name',
                        'phone',
                        'partner_id',
                    ],
                    [['id','=',users[0].company_id[0]]]);
                }).pipe(function(companies){
                    self.set('company',companies[0]);

                    return self.fetch('res.partner',['contact_address'],[['id','=',companies[0].partner_id[0]]]);
                }).pipe(function(company_partners){
                    self.get('company').contact_address = company_partners[0].contact_address;

                    return self.fetch('res.currency',['symbol','position'],[['id','=',self.get('company').currency_id[0]]]);
                }).pipe(function(currencies){
                    self.set('currency',currencies[0]);

                    return self.fetch('product.uom', null, null);
                }).pipe(function(units){
                    self.set('units',units);
                    var units_by_id = {};
                    for(var i = 0, len = units.length; i < len; i++){
                        units_by_id[units[i].id] = units[i];
                    }
                    self.set('units_by_id',units_by_id);
                    
                    return self.fetch('product.packaging', null, null);
                }).pipe(function(packagings){
                    self.set('product.packaging',packagings);

                    return self.fetch('res.users', ['name','ean13'], [['ean13', '!=', false]]);
                }).pipe(function(users){
                    self.set('user_list',users);

                    return self.fetch('account.tax', ['amount', 'price_include', 'type']);
                }).pipe(function(taxes){
                    self.set('taxes', taxes);

                    return self.fetch(
                        'pos.session', 
                        ['id', 'journal_ids','name','user_id','config_id','start_at','stop_at'],
                        [['state', '=', 'opened'], ['user_id', '=', self.session.uid]]
                    );
                }).pipe(function(sessions){
                    self.set('pos_session', sessions[0]);

                    return self.fetch(
                        'pos.config',
                        ['name','journal_ids','shop_id','journal_id',
                         'iface_self_checkout', 'iface_led', 'iface_cashdrawer',
                         'iface_payment_terminal', 'iface_electronic_scale', 'iface_barscan', 'iface_vkeyboard',
                         'iface_print_via_proxy','iface_cashdrawer','state','sequence_id','session_ids'],
                        [['id','=', self.get('pos_session').config_id[0]]]
                    );
                }).pipe(function(configs){
                    var pos_config = configs[0];
                    self.set('pos_config', pos_config);
                    self.iface_electronic_scale    =  !!pos_config.iface_electronic_scale;  
                    self.iface_print_via_proxy     =  !!pos_config.iface_print_via_proxy;
                    self.iface_vkeyboard           =  !!pos_config.iface_vkeyboard; 
                    self.iface_self_checkout       =  !!pos_config.iface_self_checkout;
                    self.iface_cashdrawer          =  !!pos_config.iface_cashdrawer;

                    return self.fetch('sale.shop',[],[['id','=',pos_config.shop_id[0]]]);
                }).pipe(function(shops){
                    self.set('shop',shops[0]);

                    return self.fetch('pos.category', ['id','name','parent_id','child_id','image'])
                }).pipe(function(categories){
                    self.db.add_categories(categories);

                    return self.fetch(
                        'product.product', 
                        ['name', 'list_price','price','pos_categ_id', 'taxes_id', 'ean13', 
                         'to_weight', 'uom_id', 'uos_id', 'uos_coeff', 'mes_type', 
                         'description_sale', 'description','dont_vidange'],
                        [['pos_categ_id','!=', false],['sale_ok','=',true]],
                        {pricelist: self.get('shop').pricelist_id[0]} // context for price
                    );
                }).pipe(function(products){
                    self.db.add_products(products);

                    return self.fetch(
                        'account.bank.statement',
                        ['account_id','currency','journal_id','state','name','user_id','pos_session_id'],
                        [['state','=','open'],['pos_session_id', '=', self.get('pos_session').id]]
                    );
                }).pipe(function(bank_statements){
                    self.set('bank_statements', bank_statements);

                    return self.fetch('account.journal', undefined, [['user_id','=', self.get('pos_session').user_id[0]]]);
                }).pipe(function(journals){
                    self.set('journals',journals);

                    // associate the bank statements with their journals. 
                    var bank_statements = self.get('bank_statements');
                    for(var i = 0, ilen = bank_statements.length; i < ilen; i++){
                        for(var j = 0, jlen = journals.length; j < jlen; j++){
                            if(bank_statements[i].journal_id[0] === journals[j].id){
                                bank_statements[i].journal = journals[j];
                                bank_statements[i].self_checkout_payment_method = journals[j].self_checkout_payment_method;
                            }
                        }
                    }
                    self.set({'cashRegisters' : new module.CashRegisterCollection(self.get('bank_statements'))});
                    self.log_loaded_data();
                });
            
        
            return loaded;
        },
    });
    module.ProductListWidget = module.ProductListWidget.extend({
        template_empty: 'ProductEmptyListWidget',
        get_category: function(){
            return this.getParent().product_categories_widget.category;
        },
        renderElement: function(){
            var ss = this.pos_widget.screen_selector;
            console.log('ss',ss);
            if(this.get_category().name === 'Root' && ss && ss.get_user_mode() === 'cashier'){
                this.replaceElement(_.str.trim(QWeb.render(this.template_empty,{widget:this})));
            }else{
                this._super();
            }
        },
    });
};
            
        
    
