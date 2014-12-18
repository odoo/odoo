openerp.point_of_sale.load_models = function load_models(instance, module){ //module is instance.point_of_sale
    "use strict";

    var QWeb = instance.web.qweb;
	var _t = instance.web._t;
    var barcode_parser_module = instance.barcodes;

    var round_di = instance.web.round_decimals;
    var round_pr = instance.web.round_precision
    
    // The PosModel contains the Point Of Sale's representation of the backend.
    // Since the PoS must work in standalone ( Without connection to the server ) 
    // it must contains a representation of the server's PoS backend. 
    // (taxes, product list, configuration options, etc.)  this representation
    // is fetched and stored by the PosModel at the initialisation. 
    // this is done asynchronously, a ready deferred alows the GUI to wait interactively 
    // for the loading to be completed 
    // There is a single instance of the PosModel for each Front-End instance, it is usually called
    // 'pos' and is available to all widgets extending PosWidget.

    module.PosModel = Backbone.Model.extend({
        initialize: function(session, attributes) {
            Backbone.Model.prototype.initialize.call(this, attributes);
            var  self = this;
            this.session = session;                 
            this.flush_mutex = new $.Mutex();                   // used to make sure the orders are sent to the server once at time
            this.pos_widget = attributes.pos_widget;

            this.proxy = new module.ProxyDevice(this);              // used to communicate to the hardware devices via a local proxy
            this.barcode_reader = new module.BarcodeReader({'pos': this, proxy:this.proxy});

            this.proxy_queue = new module.JobQueue();           // used to prevent parallels communications to the proxy
            this.db = new module.PosDB();                       // a local database used to search trough products and categories & store pending orders
            this.debug = jQuery.deparam(jQuery.param.querystring()).debug !== undefined;    //debug mode 
            
            // Business data; loaded from the server at launch
            this.accounting_precision = 2; //TODO
            this.company_logo = null;
            this.company_logo_base64 = '';
            this.currency = null;
            this.shop = null;
            this.company = null;
            this.user = null;
            this.users = [];
            this.partners = [];
            this.cashier = null;
            this.cashregisters = [];
            this.taxes = [];
            this.pos_session = null;
            this.config = null;
            this.units = [];
            this.units_by_id = {};
            this.pricelist = null;
            this.order_sequence = 1;
            window.posmodel = this;

            // these dynamic attributes can be watched for change by other models or widgets
            this.set({
                'synch':            { state:'connected', pending:0 }, 
                'orders':           new module.OrderCollection(),
                'selectedOrder':    null,
            });

            this.bind('change:synch',function(pos,synch){
                clearTimeout(self.synch_timeout);
                self.synch_timeout = setTimeout(function(){
                    if(synch.state !== 'disconnected' && synch.pending > 0){
                        self.set('synch',{state:'disconnected', pending:synch.pending});
                    }
                },3000);
            });

            this.get('orders').bind('remove', function(order,_unused_,options){ 
                self.on_removed_order(order,options.index,options.reason); 
            });
            
            // We fetch the backend data on the server asynchronously. this is done only when the pos user interface is launched,
            // Any change on this data made on the server is thus not reflected on the point of sale until it is relaunched. 
            // when all the data has loaded, we compute some stuff, and declare the Pos ready to be used. 
            this.ready = this.load_server_data()
                .then(function(){
                    if(self.config.use_proxy){
                        return self.connect_to_proxy();
                    }
                });  // used to read barcodes);
        },

        // releases ressources holds by the model at the end of life of the posmodel
        destroy: function(){
            // FIXME, should wait for flushing, return a deferred to indicate successfull destruction
            // this.flush();
            this.proxy.close();
            this.barcode_reader.disconnect();
            this.barcode_reader.disconnect_from_proxy();
        },
        connect_to_proxy: function(){
            var self = this;
            var  done = new $.Deferred();
            this.barcode_reader.disconnect_from_proxy();
            this.pos_widget.loading_message(_t('Connecting to the PosBox'),0);
            this.pos_widget.loading_skip(function(){
                    self.proxy.stop_searching();
                });
            this.proxy.autoconnect({
                    force_ip: self.config.proxy_ip || undefined,
                    progress: function(prog){ 
                        self.pos_widget.loading_progress(prog);
                    },
                }).then(function(){
                    if(self.config.iface_scan_via_proxy){
                        self.barcode_reader.connect_to_proxy();
                    }
                }).always(function(){
                    done.resolve();
                });
            return done;
        },

        // helper function to load data from the server. Obsolete use the models loader below.
        fetch: function(model, fields, domain, ctx){
            this._load_progress = (this._load_progress || 0) + 0.05; 
            this.pos_widget.loading_message(_t('Loading')+' '+model,this._load_progress);
            return new instance.web.Model(model).query(fields).filter(domain).context(ctx).all()
        },

        // Server side model loaders. This is the list of the models that need to be loaded from
        // the server. The models are loaded one by one by this list's order. The 'loaded' callback
        // is used to store the data in the appropriate place once it has been loaded. This callback
        // can return a deferred that will pause the loading of the next module. 
        // a shared temporary dictionary is available for loaders to communicate private variables
        // used during loading such as object ids, etc. 
        models: [
        {
            model:  'res.users',
            fields: ['name','company_id'],
            ids:    function(self){ return [self.session.uid]; },
            loaded: function(self,users){ self.user = users[0]; },
        },{ 
            model:  'res.company',
            fields: [ 'currency_id', 'email', 'website', 'company_registry', 'vat', 'name', 'phone', 'partner_id' , 'country_id'],
            ids:    function(self){ return [self.user.company_id[0]] },
            loaded: function(self,companies){ self.company = companies[0]; },
        },{
            model:  'decimal.precision',
            fields: ['name','digits'],
            loaded: function(self,dps){
                self.dp  = {};
                for (var i = 0; i < dps.length; i++) {
                    self.dp[dps[i].name] = dps[i].digits;
                }
            },
        },{ 
            model:  'product.uom',
            fields: [],
            domain: null,
            loaded: function(self,units){
                self.units = units;
                var units_by_id = {};
                for(var i = 0, len = units.length; i < len; i++){
                    units_by_id[units[i].id] = units[i];
                    units[i].groupable = ( units[i].category_id[0] === 1 );
                    units[i].is_unit   = ( units[i].id === 1 );
                }
                self.units_by_id = units_by_id;
            }
        },{
            model:  'res.partner',
            fields: ['name','street','city','state_id','country_id','vat','phone','zip','mobile','email','barcode','write_date'],
            domain: [['customer','=',true]], 
            loaded: function(self,partners){
                self.partners = partners;
                self.db.add_partners(partners);
            },
        },{
            model:  'res.country',
            fields: ['name'],
            loaded: function(self,countries){
                self.countries = countries;
                self.company.country = null;
                for (var i = 0; i < countries.length; i++) {
                    if (countries[i].id === self.company.country_id[0]){
                        self.company.country = countries[i];
                    }
                }
            },
        },{
            model:  'account.tax',
            fields: ['name','amount', 'price_include', 'type'],
            domain: null,
            loaded: function(self,taxes){ 
                self.taxes = taxes; 
                self.taxes_by_id = {};
                
                for (var i = 0; i < taxes.length; i++) {
                    self.taxes_by_id[taxes[i].id] = taxes[i];
                }
            },
        },{
            model:  'pos.session',
            fields: ['id', 'journal_ids','name','user_id','config_id','start_at','stop_at','sequence_number','login_number'],
            domain: function(self){ return [['state','=','opened'],['user_id','=',self.session.uid]]; },
            loaded: function(self,pos_sessions){
                self.pos_session = pos_sessions[0]; 
            },
        },{
            model: 'pos.config',
            fields: [],
            domain: function(self){ return [['id','=', self.pos_session.config_id[0]]]; },
            loaded: function(self,configs){
                self.config = configs[0];
                self.config.use_proxy = self.config.iface_payment_terminal || 
                                        self.config.iface_electronic_scale ||
                                        self.config.iface_print_via_proxy  ||
                                        self.config.iface_scan_via_proxy   ||
                                        self.config.iface_cashdrawer;

                if (self.config.company_id[0] !== self.user.company_id[0]) {
                    throw new Error(_t("Error: The Point of Sale User must belong to the same company as the Point of Sale. You are probably trying to load the point of sale as an administrator in a multi-company setup, with the administrator account set to the wrong company."));
                }

                self.db.set_uuid(self.config.uuid);

                var orders = self.db.get_orders();
                for (var i = 0; i < orders.length; i++) {
                    self.pos_session.sequence_number = Math.max(self.pos_session.sequence_number, orders[i].data.sequence_number+1);
                }
           },
        },{
            model:  'res.users',
            fields: ['name','pos_security_pin','groups_id','barcode'],
            domain: function(self){ return [['company_id','=',self.user.company_id[0]],'|', ['groups_id','=', self.config.group_pos_manager_id[0]],['groups_id','=', self.config.group_pos_user_id[0]]]; },
            loaded: function(self,users){ 
                // we attribute a role to the user, 'cashier' or 'manager', depending
                // on the group the user belongs. 
                var pos_users = [];
                for (var i = 0; i < users.length; i++) {
                    var user = users[i];
                    for (var j = 0; j < user.groups_id.length; j++) {
                        var group_id = user.groups_id[j];
                        if (group_id === self.config.group_pos_manager_id[0]) {
                            user.role = 'manager';
                            break;
                        } else if (group_id === self.config.group_pos_user_id[0]) {
                            user.role = 'cashier';
                        }
                    }
                    if (user.role) {
                        pos_users.push(user);
                    }
                    // replace the current user with its updated version
                    if (user.id === self.user.id) {
                        self.user = user;
                    }
                }
                self.users = pos_users; 
            },
        },{
            model: 'stock.location',
            fields: [],
            ids:    function(self){ return [self.config.stock_location_id[0]]; },
            loaded: function(self, locations){ self.shop = locations[0]; },
        },{
            model:  'product.pricelist',
            fields: ['currency_id'],
            ids:    function(self){ return [self.config.pricelist_id[0]]; },
            loaded: function(self, pricelists){ self.pricelist = pricelists[0]; },
        },{
            model: 'res.currency',
            fields: ['symbol','position','rounding','accuracy'],
            ids:    function(self){ return [self.pricelist.currency_id[0]]; },
            loaded: function(self, currencies){
                self.currency = currencies[0];
                if (self.currency.rounding > 0) {
                    self.currency.decimals = Math.ceil(Math.log(1.0 / self.currency.rounding) / Math.log(10));
                } else {
                    self.currency.decimals = 0;
                }

            },
        },{
            model: 'product.packaging',
            fields: ['barcode','product_tmpl_id'],
            domain: null,
            loaded: function(self, packagings){ 
                self.db.add_packagings(packagings);
            },
        },{
            model:  'pos.category',
            fields: ['id','name','parent_id','child_id','image'],
            domain: null,
            loaded: function(self, categories){
                self.db.add_categories(categories);
            },
        },{
            model:  'product.product',
            fields: ['display_name', 'list_price','price','pos_categ_id', 'taxes_id', 'barcode', 'default_code', 
                     'to_weight', 'uom_id', 'uos_id', 'uos_coeff', 'mes_type', 'description_sale', 'description',
                     'product_tmpl_id'],
            order:  ['sequence','name'],
            domain: [['sale_ok','=',true],['available_in_pos','=',true]],
            context: function(self){ return { pricelist: self.pricelist.id, display_default_code: false }; },
            loaded: function(self, products){
                self.db.add_products(products);
            },
        },{
            model:  'account.bank.statement',
            fields: ['account_id','currency','journal_id','state','name','user_id','pos_session_id'],
            domain: function(self){ return [['state', '=', 'open'],['pos_session_id', '=', self.pos_session.id]]; },
            loaded: function(self, cashregisters, tmp){
                self.cashregisters = cashregisters;

                tmp.journals = [];
                _.each(cashregisters,function(statement){
                    tmp.journals.push(statement.journal_id[0]);
                });
            },
        },{
            model:  'account.journal',
            fields: [],
            domain: function(self,tmp){ return [['id','in',tmp.journals]]; },
            loaded: function(self, journals){
                self.journals = journals;

                // associate the bank statements with their journals. 
                var cashregisters = self.cashregisters;
                for(var i = 0, ilen = cashregisters.length; i < ilen; i++){
                    for(var j = 0, jlen = journals.length; j < jlen; j++){
                        if(cashregisters[i].journal_id[0] === journals[j].id){
                            cashregisters[i].journal = journals[j];
                        }
                    }
                }

                self.cashregisters_by_id = {};
                for (var i = 0; i < self.cashregisters.length; i++) {
                    self.cashregisters_by_id[self.cashregisters[i].id] = self.cashregisters[i];
                }

                self.cashregisters = self.cashregisters.sort(function(a,b){ 
                    return a.journal.sequence - b.journal.sequence; 
                });

            },
        },  {
            label: 'fonts',
            loaded: function(self){
                var fonts_loaded = new $.Deferred();
                // Waiting for fonts to be loaded to prevent receipt printing
                // from printing empty receipt while loading Inconsolata
                // ( The font used for the receipt ) 
                waitForWebfonts(['Lato','Inconsolata'], function(){
                    fonts_loaded.resolve();
                });
                // The JS used to detect font loading is not 100% robust, so
                // do not wait more than 5sec
                setTimeout(function(){
                    fonts_loaded.resolve();
                },5000);

                return fonts_loaded;
            },
        },{
            label: 'pictures',
            loaded: function(self){
                self.company_logo = new Image();
                var  logo_loaded = new $.Deferred();
                self.company_logo.onload = function(){
                    var img = self.company_logo;
                    var ratio = 1;
                    var targetwidth = 300;
                    var maxheight = 150;
                    if( img.width !== targetwidth ){
                        ratio = targetwidth / img.width;
                    }
                    if( img.height * ratio > maxheight ){
                        ratio = maxheight / img.height;
                    }
                    var width  = Math.floor(img.width * ratio);
                    var height = Math.floor(img.height * ratio);
                    var c = document.createElement('canvas');
                        c.width  = width;
                        c.height = height
                    var ctx = c.getContext('2d');
                        ctx.drawImage(self.company_logo,0,0, width, height);

                    self.company_logo_base64 = c.toDataURL();
                    logo_loaded.resolve();
                };
                self.company_logo.onerror = function(){
                    logo_loaded.reject();
                };
                    self.company_logo.crossOrigin = "anonymous";
                self.company_logo.src = '/web/binary/company_logo' +'?_'+Math.random();

                return logo_loaded;
            },
        }, {
            label: 'barcodes',
            loaded: function(self) {
                var barcode_parser = new barcode_parser_module.BarcodeParser({'nomenclature_id': self.config.barcode_nomenclature_id});
                self.barcode_reader.set_barcode_parser(barcode_parser);
                return barcode_parser.is_loaded();
            },
        }
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
                    self.pos_widget.loading_message(_t('Loading')+' '+(model.label || model.model || ''), progress);

                    var cond = typeof model.condition === 'function'  ? model.condition(self,tmp) : true;
                    if (!cond) {
                        load_model(index+1);
                        return;
                    }

                    var fields =  typeof model.fields === 'function'  ? model.fields(self,tmp)  : model.fields;
                    var domain =  typeof model.domain === 'function'  ? model.domain(self,tmp)  : model.domain;
                    var context = typeof model.context === 'function' ? model.context(self,tmp) : model.context; 
                    var ids     = typeof model.ids === 'function'     ? model.ids(self,tmp) : model.ids;
                    var order   = typeof model.order === 'function'   ? model.order(self,tmp):    model.order;
                    progress += progress_step;
                    

                    if( model.model ){
                        if (model.ids) {
                            var records = new instance.web.Model(model.model).call('read',[ids,fields],context);
                        } else {
                            var records = new instance.web.Model(model.model).query(fields).filter(domain).order_by(order).context(context).all()
                        }
                        records.then(function(result){
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

        // reload the list of partner, returns as a deferred that resolves if there were
        // updated partners, and fails if not
        load_new_partners: function(){
            var self = this;
            var def  = new $.Deferred();
            var fields = _.find(this.models,function(model){ return model.model === 'res.partner'; }).fields;
            new instance.web.Model('res.partner')
                .query(fields)
                .filter([['write_date','>',this.db.get_partner_write_date()]])
                .all({'timeout':3000, 'shadow': true})
                .then(function(partners){
                    if (self.db.add_partners(partners)) {   // check if the partners we got were real updates
                        def.resolve();
                    } else {
                        def.reject();
                    }
                }, function(err,event){ event.preventDefault(); def.reject(); });    
            return def;
        },

        // this is called when an order is removed from the order collection. It ensures that there is always an existing
        // order and a valid selected order
        on_removed_order: function(removed_order,index,reason){
            var order_list = this.get_order_list();
            if( (reason === 'abandon' || removed_order.temporary) && order_list.length > 0){
                // when we intentionally remove an unfinished order, and there is another existing one
                this.set_order(order_list[index] || order_list[order_list.length -1]);
            }else{
                // when the order was automatically removed after completion, 
                // or when we intentionally delete the only concurrent order
                this.add_new_order();
            }
        },

        // returns the user who is currently the cashier for this point of sale
        get_cashier: function(){
            return this.cashier || this.user;
        },
        // changes the current cashier
        set_cashier: function(user){
            this.cashier = user;
        },
        //creates a new empty order and sets it as the current order
        add_new_order: function(){
            var order = new module.Order({},{pos:this});
            this.get('orders').add(order);
            this.set('selectedOrder', order);
            return order;
        },
        // load the locally saved unpaid orders for this session.
        load_orders: function(){
            var jsons = this.db.get_unpaid_orders();
            var orders = [];
            var not_loaded_count = 0; 

            for (var i = 0; i < jsons.length; i++) {
                var json = jsons[i];
                if (json.pos_session_id === this.pos_session.id) {
                    orders.push(new module.Order({},{
                        pos:  this,
                        json: json,
                    }));
                } else {
                    not_loaded_count += 1;
                }
            }

            if (not_loaded_count) {
                console.info('There are '+not_loaded_count+' locally saved unpaid orders belonging to another session');
            }
            
            orders = orders.sort(function(a,b){
                return a.sequence_number - b.sequence_number;
            });

            if (orders.length) {
                this.get('orders').add(orders);
            }
        },

        set_start_order: function(){
            var orders = this.get('orders').models;
            
            if (orders.length && !this.get('selectedOrder')) {
                this.set('selectedOrder',orders[0]);
            } else {
                this.add_new_order();
            }
        },

        // return the current order
        get_order: function(){
            return this.get('selectedOrder');
        },

        // change the current order
        set_order: function(order){
            this.set({ selectedOrder: order });
        },
        
        // return the list of unpaid orders
        get_order_list: function(){
            return this.get('orders').models;
        },

        //removes the current order
        delete_current_order: function(){
            var order = this.get_order();
            if (order) {
                order.destroy({'reason':'abandon'});
            }
        },

        // saves the order locally and try to send it to the backend. 
        // it returns a deferred that succeeds after having tried to send the order and all the other pending orders.
        push_order: function(order) {
            var self = this;

            if(order){
                this.proxy.log('push_order',order.export_as_JSON());
                this.db.add_order(order.export_as_JSON());
            }
            
            var pushed = new $.Deferred();

            this.flush_mutex.exec(function(){
                var flushed = self._flush_orders(self.db.get_orders());

                flushed.always(function(ids){
                    pushed.resolve();
                });
            });
            return pushed;
        },

        // saves the order locally and try to send it to the backend and make an invoice
        // returns a deferred that succeeds when the order has been posted and successfully generated
        // an invoice. This method can fail in various ways:
        // error-no-client: the order must have an associated partner_id. You can retry to make an invoice once
        //     this error is solved
        // error-transfer: there was a connection error during the transfer. You can retry to make the invoice once
        //     the network connection is up 

        push_and_invoice_order: function(order){
            var self = this;
            var invoiced = new $.Deferred(); 

            if(!order.get_client()){
                invoiced.reject('error-no-client');
                return invoiced;
            }

            var order_id = this.db.add_order(order.export_as_JSON());

            this.flush_mutex.exec(function(){
                var done = new $.Deferred(); // holds the mutex

                // send the order to the server
                // we have a 30 seconds timeout on this push.
                // FIXME: if the server takes more than 30 seconds to accept the order,
                // the client will believe it wasn't successfully sent, and very bad
                // things will happen as a duplicate will be sent next time
                // so we must make sure the server detects and ignores duplicated orders

                var transfer = self._flush_orders([self.db.get_order(order_id)], {timeout:30000, to_invoice:true});
                
                transfer.fail(function(){
                    invoiced.reject('error-transfer');
                    done.reject();
                });

                // on success, get the order id generated by the server
                transfer.pipe(function(order_server_id){    

                    // generate the pdf and download it
                    self.pos_widget.do_action('point_of_sale.pos_invoice_report',{additional_context:{ 
                        active_ids:order_server_id,
                    }});

                    invoiced.resolve();
                    done.resolve();
                });

                return done;

            });

            return invoiced;
        },

        // wrapper around the _save_to_server that updates the synch status widget
        _flush_orders: function(orders, options) {
            var self = this;
            this.set('synch',{ state: 'connecting', pending: orders.length});

            return self._save_to_server(orders, options).done(function (server_ids) {
                var pending = self.db.get_orders().length;

                self.set('synch', {
                    state: pending ? 'connecting' : 'connected',
                    pending: pending
                });

                return server_ids;
            });
        },

        // send an array of orders to the server
        // available options:
        // - timeout: timeout for the rpc call in ms
        // returns a deferred that resolves with the list of
        // server generated ids for the sent orders
        _save_to_server: function (orders, options) {
            if (!orders || !orders.length) {
                var result = $.Deferred();
                result.resolve([]);
                return result;
            }
                
            options = options || {};

            var self = this;
            var timeout = typeof options.timeout === 'number' ? options.timeout : 7500 * orders.length;

            // we try to send the order. shadow prevents a spinner if it takes too long. (unless we are sending an invoice,
            // then we want to notify the user that we are waiting on something )
            var posOrderModel = new instance.web.Model('pos.order');
            return posOrderModel.call('create_from_ui',
                [_.map(orders, function (order) {
                    order.to_invoice = options.to_invoice || false;
                    return order;
                })],
                undefined,
                {
                    shadow: !options.to_invoice,
                    timeout: timeout
                }
            ).then(function (server_ids) {
                _.each(orders, function (order) {
                    self.db.remove_order(order.id);
                });
                return server_ids;
            }).fail(function (error, event){
                if(error.code === 200 ){    // Business Logic Error, not a connection problem
                    //if warning do not need to display traceback!!
                    if (error.data.exception_type == 'warning') {
                        delete error.data.debug;
                    }
                    self.pos_widget.screen_selector.show_popup('error-traceback',{
                        message: error.data.message,
                        comment: error.data.debug
                    });
                }
                // prevent an error popup creation by the rpc failure
                // we want the failure to be silent as we send the orders in the background
                event.preventDefault();
                console.error('Failed to send orders:', orders);
            });
        },

        scan_product: function(parsed_code){
            var self = this;
            var selectedOrder = this.get_order();       
            var product = this.db.get_product_by_barcode(parsed_code.base_code);

            if(!product){
                return false;
            }

            if(parsed_code.type === 'price'){
                selectedOrder.add_product(product, {price:parsed_code.value});
            }else if(parsed_code.type === 'weight'){
                selectedOrder.add_product(product, {quantity:parsed_code.value, merge:false});
            }else if(parsed_code.type === 'discount'){
                selectedOrder.add_product(product, {discount:parsed_code.value, merge:false});
            }else{
                selectedOrder.add_product(product);
            }
            return true;
        },
    });

    var orderline_id = 1;

    // An orderline represent one element of the content of a client's shopping cart.
    // An orderline contains a product, its quantity, its price, discount. etc. 
    // An Order contains zero or more Orderlines.
    module.Orderline = Backbone.Model.extend({
        initialize: function(attr,options){
            this.pos   = options.pos;
            this.order = options.order;
            if (options.json) {
                this.init_from_JSON(options.json);
                return;
            }
            this.product = options.product;
            this.price   = options.product.price;
            this.quantity = 1;
            this.quantityStr = '1';
            this.discount = 0;
            this.discountStr = '0';
            this.type = 'unit';
            this.selected = false;
            this.id       = orderline_id++; 
        },
        init_from_JSON: function(json) {
            this.product = this.pos.db.get_product_by_id(json.product_id);
            if (!this.product) {
                console.error('ERROR: attempting to recover product not available in the point of sale');
            }
            this.price = json.price_unit;
            this.set_discount(json.discount);
            this.set_quantity(json.qty);
        },
        clone: function(){
            var orderline = new module.Orderline({},{
                pos: this.pos,
                order: null,
                product: this.product,
                price: this.price,
            });
            orderline.quantity = this.quantity;
            orderline.quantityStr = this.quantityStr;
            orderline.discount = this.discount;
            orderline.type = this.type;
            orderline.selected = false;
            return orderline;
        },
        // sets a discount [0,100]%
        set_discount: function(discount){
            var disc = Math.min(Math.max(parseFloat(discount) || 0, 0),100);
            this.discount = disc;
            this.discountStr = '' + disc;
            this.trigger('change',this);
        },
        // returns the discount [0,100]%
        get_discount: function(){
            return this.discount;
        },
        get_discount_str: function(){
            return this.discountStr;
        },
        get_product_type: function(){
            return this.type;
        },
        // sets the quantity of the product. The quantity will be rounded according to the 
        // product's unity of measure properties. Quantities greater than zero will not get 
        // rounded to zero
        set_quantity: function(quantity){
            if(quantity === 'remove'){
                this.order.remove_orderline(this);
                return;
            }else{
                var quant = parseFloat(quantity) || 0;
                var unit = this.get_unit();
                if(unit){
                    if (unit.rounding) {
                        this.quantity    = round_pr(quant, unit.rounding);
                        this.quantityStr = this.quantity.toFixed(Math.ceil(Math.log(1.0 / unit.rounding) / Math.log(10)));
                    } else {
                        this.quantity    = round_pr(quant, 1);
                        this.quantityStr = this.quantity.toFixed(0);
                    }
                }else{
                    this.quantity    = quant;
                    this.quantityStr = '' + this.quantity;
                }
            }
            this.trigger('change',this);
        },
        // return the quantity of product
        get_quantity: function(){
            return this.quantity;
        },
        get_quantity_str: function(){
            return this.quantityStr;
        },
        get_quantity_str_with_unit: function(){
            var unit = this.get_unit();
            if(unit && !unit.is_unit){
                return this.quantityStr + ' ' + unit.name;
            }else{
                return this.quantityStr;
            }
        },
        // return the unit of measure of the product
        get_unit: function(){
            var unit_id = this.product.uom_id;
            if(!unit_id){
                return undefined;
            }
            unit_id = unit_id[0];
            if(!this.pos){
                return undefined;
            }
            return this.pos.units_by_id[unit_id];
        },
        // return the product of this orderline
        get_product: function(){
            return this.product;
        },
        // selects or deselects this orderline
        set_selected: function(selected){
            this.selected = selected;
            this.trigger('change',this);
        },
        // returns true if this orderline is selected
        is_selected: function(){
            return this.selected;
        },
        // when we add an new orderline we want to merge it with the last line to see reduce the number of items
        // in the orderline. This returns true if it makes sense to merge the two
        can_be_merged_with: function(orderline){
            if( this.get_product().id !== orderline.get_product().id){    //only orderline of the same product can be merged
                return false;
            }else if(!this.get_unit() || !this.get_unit().groupable){
                return false;
            }else if(this.get_product_type() !== orderline.get_product_type()){
                return false;
            }else if(this.get_discount() > 0){             // we don't merge discounted orderlines
                return false;
            }else if(this.price !== orderline.price){
                return false;
            }else{ 
                return true;
            }
        },
        merge: function(orderline){
            this.set_quantity(this.get_quantity() + orderline.get_quantity());
        },
        export_as_JSON: function() {
            return {
                qty: this.get_quantity(),
                price_unit: this.get_unit_price(),
                discount: this.get_discount(),
                product_id: this.get_product().id,
            };
        },
        //used to create a json of the ticket, to be sent to the printer
        export_for_printing: function(){
            return {
                quantity:           this.get_quantity(),
                unit_name:          this.get_unit().name,
                price:              this.get_unit_display_price(),
                discount:           this.get_discount(),
                product_name:       this.get_product().display_name,
                price_display :     this.get_display_price(),
                price_with_tax :    this.get_price_with_tax(),
                price_without_tax:  this.get_price_without_tax(),
                tax:                this.get_tax(),
                product_description:      this.get_product().description,
                product_description_sale: this.get_product().description_sale,
            };
        },
        // changes the base price of the product for this orderline
        set_unit_price: function(price){
            this.price = round_di(parseFloat(price) || 0, this.pos.dp['Product Price']);
            this.trigger('change',this);
        },
        get_unit_price: function(){
            return this.price;
        },
        get_unit_display_price: function(){
            if (this.pos.config.iface_tax_included) {
                var quantity = this.quantity;
                this.quantity = 1.0;
                var price = this.get_all_prices().priceWithTax;
                this.quantity = quantity;
                return price;
            } else {
                return this.get_unit_price();
            }
        },
        get_base_price:    function(){
            var rounding = this.pos.currency.rounding;
            return  round_pr(round_pr(this.get_unit_price() * this.get_quantity(),rounding) * (1- this.get_discount()/100.0),rounding);
        },
        get_display_price: function(){
            return this.get_base_price();
            if (this.pos.config.iface_tax_included) {
                return this.get_all_prices().priceWithTax;
            } else {
                return this.get_base_price();
            }
        },
        get_price_without_tax: function(){
            return this.get_all_prices().priceWithoutTax;
        },
        get_price_with_tax: function(){
            return this.get_all_prices().priceWithTax;
        },
        get_tax: function(){
            return this.get_all_prices().tax;
        },
        get_tax_details: function(){
            return this.get_all_prices().taxDetails;
        },
        get_taxes: function(){
            var taxes_ids = this.get_product().taxes_id;
            var taxes = [];
            for (var i = 0; i < taxes_ids.length; i++) {
                taxes.push(this.pos.taxes_by_id[taxes_ids[i]]);
            }
            return taxes;
        },
        get_all_prices: function(){
            var self = this;
            var currency_rounding = this.pos.currency.rounding;
            var base = this.get_base_price();
            var totalTax = base;
            var totalNoTax = base;
            
            var product =  this.get_product(); 
            var taxes_ids = product.taxes_id;
            var taxes =  self.pos.taxes;
            var taxtotal = 0;
            var taxdetail = {};
            _.each(taxes_ids, function(el) {
                var tax = _.detect(taxes, function(t) {return t.id === el;});
                if (tax.price_include) {
                    var tmp;
                    if (tax.type === "percent") {
                        tmp =  base - round_pr(base / (1 + tax.amount),currency_rounding); 
                    } else if (tax.type === "fixed") {
                        tmp = round_pr(tax.amount * self.get_quantity(),currency_rounding);
                    } else {
                        throw "This type of tax is not supported by the point of sale: " + tax.type;
                    }
                    tmp = round_pr(tmp,currency_rounding);
                    taxtotal += tmp;
                    totalNoTax -= tmp;
                    taxdetail[tax.id] = tmp;
                } else {
                    var tmp;
                    if (tax.type === "percent") {
                        tmp = tax.amount * base;
                    } else if (tax.type === "fixed") {
                        tmp = tax.amount * self.get_quantity();
                    } else {
                        throw "This type of tax is not supported by the point of sale: " + tax.type;
                    }
                    tmp = round_pr(tmp,currency_rounding);
                    taxtotal += tmp;
                    totalTax += tmp;
                    taxdetail[tax.id] = tmp;
                }
            });
            return {
                "priceWithTax": totalTax,
                "priceWithoutTax": totalNoTax,
                "tax": taxtotal,
                "taxDetails": taxdetail,
            };
        },
    });

    module.OrderlineCollection = Backbone.Collection.extend({
        model: module.Orderline,
    });

    // Every Paymentline contains a cashregister and an amount of money.
    module.Paymentline = Backbone.Model.extend({
        initialize: function(attributes, options) {
            this.pos = options.pos;
            this.amount = 0;
            this.selected = false;
            if (options.json) {
                this.init_from_JSON(options.json);
                return;
            }
            this.cashregister = options.cashregister;
            this.name = this.cashregister.journal_id[1];
        },
        init_from_JSON: function(json){
            this.amount = json.amount;
            this.cashregister = this.pos.cashregisters_by_id[json.statement_id];
            this.name = this.cashregister.journal_id[1];
        },
        //sets the amount of money on this payment line
        set_amount: function(value){
            this.amount = round_di(parseFloat(value) || 0, this.pos.currency.decimals);
            this.trigger('change',this);
        },
        // returns the amount of money on this paymentline
        get_amount: function(){
            return this.amount;
        },
        get_amount_str: function(){
            return this.amount.toFixed(this.pos.currency.decimals);
        },
        set_selected: function(selected){
            if(this.selected !== selected){
                this.selected = selected;
                this.trigger('change',this);
            }
        },
        // returns the associated cashregister
        //exports as JSON for server communication
        export_as_JSON: function(){
            return {
                name: instance.web.datetime_to_str(new Date()),
                statement_id: this.cashregister.id,
                account_id: this.cashregister.account_id[0],
                journal_id: this.cashregister.journal_id[0],
                amount: this.get_amount()
            };
        },
        //exports as JSON for receipt printing
        export_for_printing: function(){
            return {
                amount: this.get_amount(),
                journal: this.cashregister.journal_id[1],
            };
        },
    });

    module.PaymentlineCollection = Backbone.Collection.extend({
        model: module.Paymentline,
    });

    // An order more or less represents the content of a client's shopping cart (the OrderLines) 
    // plus the associated payment information (the Paymentlines) 
    // there is always an active ('selected') order in the Pos, a new one is created
    // automaticaly once an order is completed and sent to the server.
    module.Order = Backbone.Model.extend({
        initialize: function(attributes,options){
            Backbone.Model.prototype.initialize.apply(this, arguments);
            options  = options || {};

            this.init_locked    = true;
            this.pos            = options.pos; 
            this.selected_orderline   = undefined;
            this.selected_paymentline = undefined;
            this.screen_data    = {};  // see ScreenSelector
            this.temporary      = options.temporary || false;
            this.creation_date  = new Date();
            this.to_invoice     = false;
            this.orderlines     = new module.OrderlineCollection();
            this.paymentlines   = new module.PaymentlineCollection(); 
            this.pos_session_id = this.pos.pos_session.id;

            this.set({ client: null });

            if (options.json) {
                this.init_from_JSON(options.json);
            } else {
                this.sequence_number = this.pos.pos_session.sequence_number++;
                this.uid  = this.generate_unique_id();
                this.name = _t("Order ") + this.uid; 
            }

            this.on('change',              function(){ this.save_to_db("order:change"); }, this);
            this.orderlines.on('change',   function(){ this.save_to_db("orderline:change"); }, this);
            this.orderlines.on('add',      function(){ this.save_to_db("orderline:add"); }, this);
            this.orderlines.on('remove',   function(){ this.save_to_db("orderline:remove"); }, this);
            this.paymentlines.on('change', function(){ this.save_to_db("paymentline:change"); }, this);
            this.paymentlines.on('add',    function(){ this.save_to_db("paymentline:add"); }, this);
            this.paymentlines.on('remove', function(){ this.save_to_db("paymentline:rem"); }, this);

            this.init_locked = false;
            this.save_to_db();

            return this;
        },
        save_to_db: function(){
            if (!this.init_locked) {
                this.pos.db.save_unpaid_order(this);
            } 
        },
        init_from_JSON: function(json) {
            this.sequence_number = json.sequence_number;
            this.pos.pos_session.sequence_number = Math.max(this.sequence_number+1,this.pos.pos_session.sequence_number);
            this.session_id    = json.pos_session_id;
            this.uid = json.uid;
            this.name = _t("Order ") + this.uid;
            if (json.partner_id) {
                var client = this.pos.db.get_partner_by_id(json.partner_id);
                if (!client) {
                    console.error('ERROR: trying to load a parner not available in the pos');
                }
            } else {
                var client = null;
            }
            this.set_client(client);

            this.temporary = false;     // FIXME
            this.to_invoice = false;    // FIXME

            var orderlines = json.lines;
            for (var i = 0; i < orderlines.length; i++) {
                var orderline = orderlines[i][2];
                this.add_orderline(new module.Orderline({}, {pos: this.pos, order: this, json: orderline}));
            }

            var paymentlines = json.statement_ids;
            for (var i = 0; i < paymentlines.length; i++) {
                var paymentline = paymentlines[i][2];
                var newpaymentline = new module.Paymentline({},{pos: this.pos, json: paymentline});
                this.paymentlines.add(newpaymentline);

                if (i === paymentlines.length - 1) {
                    this.select_paymentline(newpaymentline);
                }
            }
        },
        export_as_JSON: function() {
            var orderLines, paymentLines;
            orderLines = [];
            this.orderlines.each(_.bind( function(item) {
                return orderLines.push([0, 0, item.export_as_JSON()]);
            }, this));
            paymentLines = [];
            this.paymentlines.each(_.bind( function(item) {
                return paymentLines.push([0, 0, item.export_as_JSON()]);
            }, this));
            return {
                name: this.get_name(),
                amount_paid: this.get_total_paid(),
                amount_total: this.get_total_with_tax(),
                amount_tax: this.get_total_tax(),
                amount_return: this.get_change(),
                lines: orderLines,
                statement_ids: paymentLines,
                pos_session_id: this.pos_session_id,
                partner_id: this.get_client() ? this.get_client().id : false,
                user_id: this.pos.cashier ? this.pos.cashier.id : this.pos.user.id,
                uid: this.uid,
                sequence_number: this.sequence_number,
            };
        },
        export_for_printing: function(){
            var orderlines = [];
            var self = this;

            this.orderlines.each(function(orderline){
                orderlines.push(orderline.export_for_printing());
            });

            var paymentlines = [];
            this.paymentlines.each(function(paymentline){
                paymentlines.push(paymentline.export_for_printing());
            });
            var client  = this.get('client');
            var cashier = this.pos.cashier || this.pos.user;
            var company = this.pos.company;
            var shop    = this.pos.shop;
            var date    = new Date();

            function is_xml(subreceipt){
                return subreceipt ? (subreceipt.split('\n')[0].indexOf('<!DOCTYPE QWEB') >= 0) : false;
            }

            function render_xml(subreceipt){
                if (!is_xml(subreceipt)) {
                    return subreceipt;
                } else {
                    subreceipt = subreceipt.split('\n').slice(1).join('\n');
                    var qweb = new QWeb2.Engine();
                        qweb.debug = instance.session.debug;
                        qweb.default_dict = _.clone(QWeb.default_dict);
                        qweb.add_template('<templates><t t-name="subreceipt">'+subreceipt+'</t></templates>');
                    
                    return qweb.render('subreceipt',{'pos':self.pos,'widget':self.pos.pos_widget,'order':self, 'receipt': receipt}) ;
                }
            }

            var receipt = {
                orderlines: orderlines,
                paymentlines: paymentlines,
                subtotal: this.get_subtotal(),
                total_with_tax: this.get_total_with_tax(),
                total_without_tax: this.get_total_without_tax(),
                total_tax: this.get_total_tax(),
                total_paid: this.get_total_paid(),
                total_discount: this.get_total_discount(),
                tax_details: this.get_tax_details(),
                change: this.get_change(),
                name : this.get_name(),
                client: client ? client.name : null ,
                invoice_id: null,   //TODO
                cashier: cashier ? cashier.name : null,
                header: this.pos.config.receipt_header || '',
                footer: this.pos.config.receipt_footer || '',
                precision: {
                    price: 2,
                    money: 2,
                    quantity: 3,
                },
                date: { 
                    year: date.getFullYear(), 
                    month: date.getMonth(), 
                    date: date.getDate(),       // day of the month 
                    day: date.getDay(),         // day of the week 
                    hour: date.getHours(), 
                    minute: date.getMinutes() ,
                    isostring: date.toISOString(),
                    localestring: date.toLocaleString(),
                }, 
                company:{
                    email: company.email,
                    website: company.website,
                    company_registry: company.company_registry,
                    contact_address: company.partner_id[1], 
                    vat: company.vat,
                    name: company.name,
                    phone: company.phone,
                    logo:  this.pos.company_logo_base64,
                },
                shop:{
                    name: shop.name,
                },
                currency: this.pos.currency,
            };
            
            if (is_xml(this.pos.config.receipt_header)){
                receipt.header_xml = render_xml(this.pos.config.receipt_header);
            }

            if (is_xml(this.pos.config.receipt_footer)){
                receipt.footer_xml = render_xml(this.pos.config.receipt_footer);
            }

            return receipt;
        },
        is_empty: function(){
            return this.orderlines.models.length === 0;
        },
        generate_unique_id: function() {
            // Generates a public identification number for the order.
            // The generated number must be unique and sequential. They are made 12 digit long
            // to fit into EAN-13 barcodes, should it be needed 

            function zero_pad(num,size){
                var s = ""+num;
                while (s.length < size) {
                    s = "0" + s;
                }
                return s;
            }
            return zero_pad(this.pos.pos_session.id,5) +'-'+
                   zero_pad(this.pos.pos_session.login_number,3) +'-'+
                   zero_pad(this.sequence_number,4);
        },
        get_name: function() {
            return this.name;
        },
        /* ---- Order Lines --- */
        add_orderline: function(line){
            if(line.order){
                line.order.remove_orderline(line);
            }
            line.order = this;
            this.orderlines.add(line);
            this.select_orderline(this.get_last_orderline());
        },
        get_orderline: function(id){
            var orderlines = this.orderlines.models;
            for(var i = 0; i < orderlines.length; i++){
                if(orderlines[i].id === id){
                    return orderlines[i];
                }
            }
            return null;
        },
        get_orderlines: function(){
            return this.orderlines.models;
        },
        get_last_orderline: function(){
            return this.orderlines.at(this.orderlines.length -1);
        },
        remove_orderline: function( line ){
            this.orderlines.remove(line);
            this.select_orderline(this.get_last_orderline());
        },
        add_product: function(product, options){
            options = options || {};
            var attr = JSON.parse(JSON.stringify(product));
            attr.pos = this.pos;
            attr.order = this;
            var line = new module.Orderline({}, {pos: this.pos, order: this, product: product});

            if(options.quantity !== undefined){
                line.set_quantity(options.quantity);
            }
            if(options.price !== undefined){
                line.set_unit_price(options.price);
            }
            if(options.discount !== undefined){
                line.set_discount(options.discount);
            }

            if(options.extras !== undefined){
                for (var prop in options.extras) { 
                    line[prop] = options.extras[prop];
                }
            }

            var last_orderline = this.get_last_orderline();
            if( last_orderline && last_orderline.can_be_merged_with(line) && options.merge !== false){
                last_orderline.merge(line);
            }else{
                this.orderlines.add(line);
            }
            this.select_orderline(this.get_last_orderline());
        },
        get_selected_orderline: function(){
            return this.selected_orderline;
        },
        select_orderline: function(line){
            if(line){
                if(line !== this.selected_orderline){
                    if(this.selected_orderline){
                        this.selected_orderline.set_selected(false);
                    }
                    this.selected_orderline = line;
                    this.selected_orderline.set_selected(true);
                }
            }else{
                this.selected_orderline = undefined;
            }
        },
        deselect_orderline: function(){
            if(this.selected_orderline){
                this.selected_orderline.set_selected(false);
                this.selected_orderline = undefined;
            }
        },
        /* ---- Payment Lines --- */
        add_paymentline: function(cashregister) {
            var newPaymentline = new module.Paymentline({},{cashregister:cashregister, pos: this.pos});
            if(cashregister.journal.type !== 'cash' || this.pos.config.iface_precompute_cash){
                newPaymentline.set_amount( Math.max(this.get_due(),0) );
            }
            this.paymentlines.add(newPaymentline);
            this.select_paymentline(newPaymentline);

        },
        get_paymentlines: function(){
            return this.paymentlines.models;
        },
        remove_paymentline: function(line){
            if(this.selected_paymentline === line){
                this.select_paymentline(undefined);
            }
            this.paymentlines.remove(line);
        },
        clean_empty_paymentlines: function() {
            var lines = this.paymentlines.models;
            var empty = [];
            for ( var i = 0; i < lines.length; i++) {
                if (!lines[i].get_amount()) {
                    empty.push(lines[i]);
                }
            }
            for ( var i = 0; i < empty.length; i++) {
                this.remove_paymentline(empty[i]);
            }
        },
        select_paymentline: function(line){
            if(line !== this.selected_paymentline){
                if(this.selected_paymentline){
                    this.selected_paymentline.set_selected(false);
                }
                this.selected_paymentline = line;
                if(this.selected_paymentline){
                    this.selected_paymentline.set_selected(true);
                }
                this.trigger('change:selected_paymentline',this.selected_paymentline);
            }
        },
        /* ---- Payment Status --- */
        get_subtotal : function(){
            return this.orderlines.reduce((function(sum, orderLine){
                return sum + orderLine.get_display_price();
            }), 0);
        },
        get_total_with_tax: function() {
            return this.orderlines.reduce((function(sum, orderLine) {
                return sum + orderLine.get_price_with_tax();
            }), 0);
        },
        get_total_without_tax: function() {
            return this.orderlines.reduce((function(sum, orderLine) {
                return sum + orderLine.get_price_without_tax();
            }), 0);
        },
        get_total_discount: function() {
            return this.orderlines.reduce((function(sum, orderLine) {
                return sum + (orderLine.get_unit_price() * (orderLine.get_discount()/100) * orderLine.get_quantity());
            }), 0);
        },
        get_total_tax: function() {
            return this.orderlines.reduce((function(sum, orderLine) {
                return sum + orderLine.get_tax();
            }), 0);
        },
        get_total_paid: function() {
            return this.paymentlines.reduce((function(sum, paymentLine) {
                return sum + paymentLine.get_amount();
            }), 0);
        },
        get_tax_details: function(){
            var details = {};
            var fulldetails = [];
            var taxes_by_id = {};
            
            for(var i = 0; i < this.pos.taxes.length; i++){
                taxes_by_id[this.pos.taxes[i].id] = this.pos.taxes[i];
            }

            this.orderlines.each(function(line){
                var ldetails = line.get_tax_details();
                for(var id in ldetails){
                    if(ldetails.hasOwnProperty(id)){
                        details[id] = (details[id] || 0) + ldetails[id];
                    }
                }
            });
            
            for(var id in details){
                if(details.hasOwnProperty(id)){
                    fulldetails.push({amount: details[id], tax: taxes_by_id[id], name: taxes_by_id[id].name});
                }
            }

            return fulldetails;
        },
        // Returns a total only for the orderlines with products belonging to the category 
        get_total_for_category_with_tax: function(categ_id){
            var total = 0;
            var self = this;

            if (categ_id instanceof Array) {
                for (var i = 0; i < categ_id.length; i++) {
                    total += this.get_total_for_category_with_tax(categ_id[i]);
                }
                return total;
            }
            
            this.orderlines.each(function(line){
                if ( self.pos.db.category_contains(categ_id,line.product.id) ) {
                    total += line.get_price_with_tax();
                }
            });

            return total;
        },
        get_total_for_taxes: function(tax_id){
            var total = 0;
            var self = this;

            if (!(tax_id instanceof Array)) {
                tax_id = [tax_id];
            }

            var tax_set = {};

            for (var i = 0; i < tax_id.length; i++) {
                tax_set[tax_id[i]] = true;
            }

            this.orderlines.each(function(line){
                var taxes_ids = line.get_product().taxes_id;
                for (var i = 0; i < taxes_ids.length; i++) {
                    if (tax_set[taxes_ids[i]]) {
                        total += line.get_price_with_tax();
                        return;
                    }
                }
            });

            return total;
        },
        get_change: function(paymentline) {
            if (!paymentline) {
                var change = this.get_total_paid() - this.get_total_with_tax();
            } else {
                var change = -this.get_total_with_tax(); 
                var lines  = this.paymentlines.models;
                for (var i = 0; i < lines.length; i++) {
                    change += lines[i].get_amount();
                    if (lines[i] === paymentline) {
                        break;
                    }
                }
            }
            return round_pr(Math.max(0,change), this.pos.currency.rounding);
        },
        get_due: function(paymentline) {
            if (!paymentline) {
                var due = this.get_total_with_tax() - this.get_total_paid();
            } else {
                var due = this.get_total_with_tax();
                var lines = this.paymentlines.models;
                for (var i = 0; i < lines.length; i++) {
                    if (lines[i] === paymentline) {
                        break;
                    } else {
                        due -= lines[i].get_amount();
                    }
                }
            }
            return round_pr(Math.max(0,due), this.pos.currency.rounding);
        },
        is_paid: function(){
            return this.get_due() === 0;
        },
        is_paid_with_cash: function(){
            return !!this.paymentlines.find( function(pl){
                return pl.cashregister.journal.type === 'cash';
            });
        },
        finalize: function(){
            this.destroy();
        },
        destroy: function(args){
            Backbone.Model.prototype.destroy.apply(this,arguments);
            this.pos.db.remove_unpaid_order(this);
        },
        /* ---- Invoice --- */
        set_to_invoice: function(to_invoice) {
            this.to_invoice = to_invoice;
        },
        is_to_invoice: function(){
            return this.to_invoice;
        },
        /* ---- Client / Customer --- */
        // the client related to the current order.
        set_client: function(client){
            this.set('client',client);
        },
        get_client: function(){
            return this.get('client');
        },
        get_client_name: function(){
            var client = this.get('client');
            return client ? client.name : "";
        },
        /* ---- Screen Status --- */
        // the order also stores the screen status, as the PoS supports
        // different active screens per order. This method is used to
        // store the screen status.
        set_screen_data: function(key,value){
            if(arguments.length === 2){
                this.screen_data[key] = value;
            }else if(arguments.length === 1){
                for(var key in arguments[0]){
                    this.screen_data[key] = arguments[0][key];
                }
            }
        },
        //see set_screen_data
        get_screen_data: function(key){
            return this.screen_data[key];
        },
    });

    module.OrderCollection = Backbone.Collection.extend({
        model: module.Order,
    });

    /*
     The numpad handles both the choice of the property currently being modified
     (quantity, price or discount) and the edition of the corresponding numeric value.
     */
    module.NumpadState = Backbone.Model.extend({
        defaults: {
            buffer: "0",
            mode: "quantity"
        },
        appendNewChar: function(newChar) {
            var oldBuffer;
            oldBuffer = this.get('buffer');
            if (oldBuffer === '0') {
                this.set({
                    buffer: newChar
                });
            } else if (oldBuffer === '-0') {
                this.set({
                    buffer: "-" + newChar
                });
            } else {
                this.set({
                    buffer: (this.get('buffer')) + newChar
                });
            }
            this.trigger('set_value',this.get('buffer'));
        },
        deleteLastChar: function() {
            if(this.get('buffer') === ""){
                if(this.get('mode') === 'quantity'){
                    this.trigger('set_value','remove');
                }else{
                    this.trigger('set_value',this.get('buffer'));
                }
            }else{
                var newBuffer = this.get('buffer').slice(0,-1) || "";
                this.set({ buffer: newBuffer });
                this.trigger('set_value',this.get('buffer'));
            }
        },
        switchSign: function() {
            var oldBuffer;
            oldBuffer = this.get('buffer');
            this.set({
                buffer: oldBuffer[0] === '-' ? oldBuffer.substr(1) : "-" + oldBuffer 
            });
            this.trigger('set_value',this.get('buffer'));
        },
        changeMode: function(newMode) {
            this.set({
                buffer: "0",
                mode: newMode
            });
        },
        reset: function() {
            this.set({
                buffer: "0",
                mode: "quantity"
            });
        },
        resetValue: function(){
            this.set({buffer:'0'});
        },
    });
}
