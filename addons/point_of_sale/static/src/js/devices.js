
function openerp_pos_devices(instance,module){ //module is instance.point_of_sale

    // the JobQueue schedules a sequence of 'jobs'. each job is
    // a function returning a deferred. the queue waits for each job to finish 
    // before launching the next. Each job can also be scheduled with a delay. 
    // the  is used to prevent parallel requests to the proxy.

    module.JobQueue = function(){
        var queue = [];
        var running = false;
        var scheduled_end_time = 0;
        var end_of_queue = (new $.Deferred()).resolve();
        var stoprepeat = false;

        var run = function(){
            if(end_of_queue.state() === 'resolved'){
                end_of_queue =  new $.Deferred();
            }
            if(queue.length > 0){
                running = true;
                var job = queue[0];
                if(!job.opts.repeat || stoprepeat){
                    queue.shift();
                    stoprepeat = false;
                }

                // the time scheduled for this job
                scheduled_end_time = (new Date()).getTime() + (job.opts.duration || 0);

                // we run the job and put in def when it finishes
                var def = job.fun() || (new $.Deferred()).resolve();
                
                // we don't care if a job fails ... 
                def.always(function(){
                    // we run the next job after the scheduled_end_time, even if it finishes before
                    setTimeout(function(){
                        run();
                    }, Math.max(0, scheduled_end_time - (new Date()).getTime()) ); 
                });
            }else{
                running = false;
                scheduled_end_time = 0;
                end_of_queue.resolve();
            }
        };
        
        // adds a job to the schedule.
        // opts : {
        //    duration    : the job is guaranteed to finish no quicker than this (milisec)
        //    repeat      : if true, the job will be endlessly repeated
        //    important   : if true, the scheduled job cannot be canceled by a queue.clear()
        // }
        this.schedule  = function(fun, opts){
            queue.push({fun:fun, opts:opts || {}});
            if(!running){
                run();
            }
        }

        // remove all jobs from the schedule (except the ones marked as important)
        this.clear = function(){
            queue = _.filter(queue,function(job){job.opts.important === true}); 
        };

        // end the repetition of the current job
        this.stoprepeat = function(){
            stoprepeat = true;
        };
        
        // returns a deferred that resolves when all scheduled 
        // jobs have been run.
        // ( jobs added after the call to this method are considered as well )
        this.finished = function(){
            return end_of_queue;
        }

    };

    // this object interfaces with the local proxy to communicate to the various hardware devices
    // connected to the Point of Sale. As the communication only goes from the POS to the proxy,
    // methods are used both to signal an event, and to fetch information. 

    module.ProxyDevice  = instance.web.Class.extend(openerp.PropertiesMixin,{
        init: function(parent,options){
            openerp.PropertiesMixin.init.call(this,parent);
            var self = this;
            options = options || {};
            url = options.url || 'http://localhost:8069';
            
            this.weighting = false;
            this.debug_weight = 0;
            this.use_debug_weight = false;

            this.paying = false;
            this.default_payment_status = {
                status: 'waiting',
                message: '',
                payment_method: undefined,
                receipt_client: undefined,
                receipt_shop:   undefined,
            };    
            this.custom_payment_status = this.default_payment_status;

            this.receipt_queue = [];

            this.notifications = {};
            this.bypass_proxy = false;

            this.connection = null; 
            this.host       = '';
            this.keptalive  = false;

            this.set('status',{});

            this.set_connection_status('disconnected');

            this.on('change:status',this,function(eh,status){
                status = status.newValue;
                if(status.status === 'connected'){
                    self.print_receipt();
                }
            });

            window.hw_proxy = this;
        },
        set_connection_status: function(status,drivers){
            oldstatus = this.get('status');
            newstatus = {};
            newstatus.status = status;
            newstatus.drivers = status === 'disconnected' ? {} : oldstatus.drivers;
            newstatus.drivers = drivers ? drivers : newstatus.drivers;
            this.set('status',newstatus);
        },
        disconnect: function(){
            if(this.get('status').status !== 'disconnected'){
                this.connection.destroy();
                this.set_connection_status('disconnected');
            }
        },

        // connects to the specified url
        connect: function(url){
            var self = this;
            this.connection = new instance.web.Session(undefined,url, { use_cors: true});
            this.host   = url;
            this.set_connection_status('connecting',{});

            return this.message('handshake').then(function(response){
                    if(response){
                        self.set_connection_status('connected');
                        localStorage['hw_proxy_url'] = url;
                        self.keepalive();
                    }else{
                        self.set_connection_status('disconnected');
                        console.error('Connection refused by the Proxy');
                    }
                },function(){
                    self.set_connection_status('disconnected');
                    console.error('Could not connect to the Proxy');
                });
        },

        // find a proxy and connects to it. for options see find_proxy
        //   - force_ip : only try to connect to the specified ip. 
        //   - port: what port to listen to (default 8069)
        //   - progress(fac) : callback for search progress ( fac in [0,1] ) 
        autoconnect: function(options){
            var self = this;
            this.set_connection_status('connecting',{});
            var found_url = new $.Deferred();
            var success = new $.Deferred();

            if ( options.force_ip ){
                // if the ip is forced by server config, bailout on fail
                found_url = this.try_hard_to_connect(options.force_ip, options)
            }else if( localStorage['hw_proxy_url'] ){
                // try harder when we remember a good proxy url
                found_url = this.try_hard_to_connect(localStorage['hw_proxy_url'], options)
                    .then(null,function(){
                        return self.find_proxy(options);
                    });
            }else{
                // just find something quick
                found_url = this.find_proxy(options);
            }

            success = found_url.then(function(url){
                    return self.connect(url);
                });

            success.fail(function(){
                self.set_connection_status('disconnected');
            });

            return success;
        },

        // starts a loop that updates the connection status
        keepalive: function(){
            var self = this;
            if(!this.keptalive){
                this.keptalive = true;
                function status(){
                    self.connection.rpc('/hw_proxy/status_json',{},{timeout:2500})       
                        .then(function(driver_status){
                            self.set_connection_status('connected',driver_status);
                        },function(){
                            if(self.get('status').status !== 'connecting'){
                                self.set_connection_status('disconnected');
                            }
                        }).always(function(){
                            setTimeout(status,5000);
                        });
                }
                status();
            };
        },

        message : function(name,params){
            var callbacks = this.notifications[name] || [];
            for(var i = 0; i < callbacks.length; i++){
                callbacks[i](params);
            }
            if(this.get('status').status !== 'disconnected'){
                return this.connection.rpc('/hw_proxy/' + name, params || {});       
            }else{
                return (new $.Deferred()).reject();
            }
        },

        // try several time to connect to a known proxy url
        try_hard_to_connect: function(url,options){
            options   = options || {};
            var port  = ':' + (options.port || '8069');

            this.set_connection_status('connecting');

            if(url.indexOf('//') < 0){
                url = 'http://'+url;
            }

            if(url.indexOf(':',5) < 0){
                url = url+port;
            }

            // try real hard to connect to url, with a 1sec timeout and up to 'retries' retries
            function try_real_hard_to_connect(url, retries, done){

                done = done || new $.Deferred();

                var c = $.ajax({
                    url: url + '/hw_proxy/hello',
                    method: 'GET',
                    timeout: 1000,
                })
                .done(function(){
                    done.resolve(url);
                })
                .fail(function(){
                    if(retries > 0){
                        try_real_hard_to_connect(url,retries-1,done);
                    }else{
                        done.reject();
                    }
                });
                return done;
            }

            return try_real_hard_to_connect(url,3);
        },

        // returns as a deferred a valid host url that can be used as proxy.
        // options:
        //   - port: what port to listen to (default 8069)
        //   - progress(fac) : callback for search progress ( fac in [0,1] ) 
        find_proxy: function(options){
            options = options || {};
            var self  = this;
            var port  = ':' + (options.port || '8069');
            var urls  = [];
            var found = false;
            var parallel = 8;
            var done = new $.Deferred(); // will be resolved with the proxies valid urls
            var threads  = [];
            var progress = 0;


            urls.push('http://localhost'+port);
            for(var i = 0; i < 256; i++){
                urls.push('http://192.168.0.'+i+port);
                urls.push('http://192.168.1.'+i+port);
                urls.push('http://10.0.0.'+i+port);
            }

            var prog_inc = 1/urls.length; 

            function update_progress(){
                progress = found ? 1 : progress + prog_inc;
                if(options.progress){
                    options.progress(progress);
                }
            }

            function thread(done){
                var url = urls.shift();

                done = done || new $.Deferred();

                if( !url || found || !self.searching_for_proxy ){ 
                    done.resolve();
                    return done;
                }

                var c = $.ajax({
                        url: url + '/hw_proxy/hello',
                        method: 'GET',
                        timeout: 400, 
                    }).done(function(){
                        found = true;
                        update_progress();
                        done.resolve(url);
                    })
                    .fail(function(){
                        update_progress();
                        thread(done);
                    });

                return done;
            }

            this.searching_for_proxy = true;

            for(var i = 0, len = Math.min(parallel,urls.length); i < len; i++){
                threads.push(thread());
            }
            
            $.when.apply($,threads).then(function(){
                var urls = [];
                for(var i = 0; i < arguments.length; i++){
                    if(arguments[i]){
                        urls.push(arguments[i]);
                    }
                }
                done.resolve(urls[0]);
            });

            return done;
        },

        stop_searching: function(){
            this.searching_for_proxy = false;
            this.set_connection_status('disconnected');
        },

        // this allows the client to be notified when a proxy call is made. The notification 
        // callback will be executed with the same arguments as the proxy call
        add_notification: function(name, callback){
            if(!this.notifications[name]){
                this.notifications[name] = [];
            }
            this.notifications[name].push(callback);
        },
        
        //a product has been scanned and recognized with success
        // ean is a parsed ean object
        scan_item_success: function(ean){
            return this.message('scan_item_success',{ean: ean});
        },

        // a product has been scanned but not recognized
        // ean is a parsed ean object
        scan_item_error_unrecognized: function(ean){
            return this.message('scan_item_error_unrecognized',{ean: ean});
        },

        //the client is asking for help
        help_needed: function(){
            return this.message('help_needed');
        },

        //the client does not need help anymore
        help_canceled: function(){
            return this.message('help_canceled');
        },

        //the client is starting to weight
        weighting_start: function(){
            var ret = new $.Deferred();
            if(!this.weighting){
                this.weighting = true;
                this.message('weighting_start').always(function(){
                    ret.resolve();
                });
            }else{
                console.error('Weighting already started!!!');
                ret.resolve();
            }
            return ret;
        },

        // the client has finished weighting products
        weighting_end: function(){
            var ret = new $.Deferred();
            if(this.weighting){
                this.weighting = false;
                this.message('weighting_end').always(function(){
                    ret.resolve();
                });
            }else{
                console.error('Weighting already ended !!!');
                ret.resolve();
            }
            return ret;
        },

        //returns the weight on the scale. 
        // is called at regular interval (up to 10x/sec) between a weighting_start()
        // and a weighting_end()
        weighting_read_kg: function(){
            var self = this;
            var ret = new $.Deferred();
            this.message('weighting_read_kg',{})
                .then(function(weight){
                    ret.resolve(self.use_debug_weight ? self.debug_weight : weight);
                }, function(){ //failed to read weight
                    ret.resolve(self.use_debug_weight ? self.debug_weight : 0.0);
                });
            return ret;
        },

        // sets a custom weight, ignoring the proxy returned value. 
        debug_set_weight: function(kg){
            this.use_debug_weight = true;
            this.debug_weight = kg;
        },

        // resets the custom weight and re-enable listening to the proxy for weight values
        debug_reset_weight: function(){
            this.use_debug_weight = false;
            this.debug_weight = 0;
        },


        // the pos asks the client to pay 'price' units
        payment_request: function(price){
            var ret = new $.Deferred();
            this.paying = true;
            this.custom_payment_status = this.default_payment_status;
            return this.message('payment_request',{'price':price});
        },

        payment_status: function(){
            if(this.bypass_proxy){
                this.bypass_proxy = false;
                return (new $.Deferred()).resolve(this.custom_payment_status);
            }else{
                return this.message('payment_status');
            }
        },
        
        // override what the proxy says and accept the payment
        debug_accept_payment: function(){
            this.bypass_proxy = true;
            this.custom_payment_status = {
                status: 'paid',
                message: 'Successfull Payment, have a nice day',
                payment_method: 'AMEX',
                receipt_client: '<xml>bla</xml>',
                receipt_shop:   '<xml>bla</xml>',
            };    
        },

        // override what the proxy says and reject the payment
        debug_reject_payment: function(){
            this.bypass_proxy = true;
            this.custom_payment_status = {
                status: 'error-rejected',
                message: 'Sorry you don\'t have enough money :(',
            };    
        },
        // the client cancels his payment
        payment_cancel: function(){
            this.paying = false;
            this.custom_payment_status = 'waiting_for_payment';
            return this.message('payment_cancel');
        },

        // called when the client logs in or starts to scan product
        transaction_start: function(){
            return this.message('transaction_start');
        },

        // called when the clients has finished his interaction with the machine
        transaction_end: function(){
            return this.message('transaction_end');
        },

        // called when the POS turns to cashier mode
        cashier_mode_activated: function(){
            return this.message('cashier_mode_activated');
        },

        // called when the POS turns to client mode
        cashier_mode_deactivated: function(){
            return this.message('cashier_mode_deactivated');
        },
        
        // ask for the cashbox (the physical box where you store the cash) to be opened
        open_cashbox: function(){
            return this.message('open_cashbox');
        },

        /* ask the printer to print a receipt
         * receipt is a JSON object with the following specs:
         * receipt{
         *  - orderlines : list of orderlines :
         *     {
         *          quantity:           (number) the number of items, or the weight, 
         *          unit_name:          (string) the name of the item's unit (kg, dozen, ...)
         *          price:              (number) the price of one unit of the item before discount
         *          discount:           (number) the discount on the product in % [0,100] 
         *          product_name:       (string) the name of the product
         *          price_with_tax:     (number) the price paid for this orderline, tax included
         *          price_without_tax:  (number) the price paid for this orderline, without taxes
         *          tax:                (number) the price paid in taxes on this orderline
         *          product_description:         (string) generic description of the product
         *          product_description_sale:    (string) sales related information of the product
         *     }
         *  - paymentlines : list of paymentlines :
         *     {
         *          amount:             (number) the amount paid
         *          journal:            (string) the name of the journal on wich the payment has been made  
         *     }
         *  - total_with_tax:     (number) the total of the receipt tax included
         *  - total_without_tax:  (number) the total of the receipt without taxes
         *  - total_tax:          (number) the total amount of taxes paid
         *  - total_paid:         (number) the total sum paid by the client
         *  - change:             (number) the amount of change given back to the client
         *  - name:               (string) a unique name for this order
         *  - client:             (string) name of the client. or null if no client is logged
         *  - cashier:            (string) the name of the cashier
         *  - date: {             the date at wich the payment has been done
         *      year:             (number) the year  [2012, ...]
         *      month:            (number) the month [0,11]
         *      date:             (number) the day of the month [1,31]
         *      day:              (number) the day of the week  [0,6] 
         *      hour:             (number) the hour [0,23]
         *      minute:           (number) the minute [0,59]
         *    }
         */
        print_receipt: function(receipt){
            var self = this;
            if(receipt){
                this.receipt_queue.push(receipt);
            }
            var aborted = false;
            function send_printing_job(){
                if (self.receipt_queue.length > 0){
                    var r = self.receipt_queue.shift();
                    self.message('print_receipt',{ receipt: r },{ timeout: 5000 })
                        .then(function(){
                            send_printing_job();
                        },function(){
                            self.receipt_queue.unshift(r)
                        });
                }
            }
            send_printing_job();
        },

        // asks the proxy to log some information, as with the debug.log you can provide several arguments.
        log: function(){
            return this.message('log',{'arguments': _.toArray(arguments)});
        },

        // asks the proxy to print an invoice in pdf form ( used to print invoices generated by the server ) 
        print_pdf_invoice: function(pdfinvoice){
            return this.message('print_pdf_invoice',{pdfinvoice: pdfinvoice});
        },
    });

    // this module interfaces with the barcode reader. It assumes the barcode reader
    // is set-up to act like  a keyboard. Use connect() and disconnect() to activate 
    // and deactivate the barcode reader. Use set_action_callbacks to tell it
    // what to do when it reads a barcode.
    module.BarcodeReader = instance.web.Class.extend({
        actions:[
            'product',
            'cashier',
            'client',
            'discount',
        ],
        init: function(attributes){
            this.pos = attributes.pos;
            this.action_callback = {};
            this.proxy = attributes.proxy;
            this.remote_scanning = false;
            this.remote_active = 0;

            this.action_callback_stack = [];

            this.weight_prefix_set   = attributes.weight_prefix_set   ||  {'21':''};
            this.discount_prefix_set = attributes.discount_prefix_set ||  {'22':''};
            this.price_prefix_set    = attributes.price_prefix_set    ||  {'23':''};
            this.cashier_prefix_set  = attributes.cashier_prefix_set  ||  {'041':''};
            this.client_prefix_set   = attributes.client_prefix_set   ||  {'042':''};

        },

        save_callbacks: function(){
            var callbacks = {};
            for(name in this.action_callback){
                callbacks[name] = this.action_callback[name];
            }
            this.action_callback_stack.push(callbacks);
        },

        restore_callbacks: function(){
            if(this.action_callback_stack.length){
                var callbacks = this.action_callback_stack.pop();
                this.action_callback = callbacks;
            }
        },
       
        // when an ean is scanned and parsed, the callback corresponding
        // to its type is called with the parsed_ean as a parameter. 
        // (parsed_ean is the result of parse_ean(ean)) 
        // 
        // callbacks is a Map of 'actions' : callback(parsed_ean)
        // that sets the callback for each action. if a callback for the
        // specified action already exists, it is replaced. 
        // 
        // possible actions include : 
        // 'product' | 'cashier' | 'client' | 'discount' 
    
        set_action_callback: function(action, callback){
            if(arguments.length == 2){
                this.action_callback[action] = callback;
            }else{
                var actions = arguments[0];
                for(action in actions){
                    this.set_action_callback(action,actions[action]);
                }
            }
        },

        //remove all action callbacks 
        reset_action_callbacks: function(){
            for(action in this.action_callback){
                this.action_callback[action] = undefined;
            }
        },
        // returns the checksum of the ean, or -1 if the ean has not the correct length, ean must be a string
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
        // returns true if the ean is a valid EAN codebar number by checking the control digit.
        // ean must be a string
        check_ean: function(ean){
            return /^\d+$/.test(ean) && this.ean_checksum(ean) === Number(ean[ean.length-1]);
        },
        // returns a valid zero padded ean13 from an ean prefix. the ean prefix must be a string.
        sanitize_ean:function(ean){
            ean = ean.substr(0,13);

            for(var n = 0, count = (13 - ean.length); n < count; n++){
                ean = ean + '0';
            }
            return ean.substr(0,12) + this.ean_checksum(ean);
        },
        
        // attempts to interpret an ean (string encoding an ean)
        // it will check its validity then return an object containing various
        // information about the ean.
        // most importantly : 
        // - code    : the ean
        // - type   : the type of the ean: 
        //      'price' |  'weight' | 'unit' | 'cashier' | 'client' | 'discount' | 'error'
        //
        // - prefix : the prefix that has ben used to determine the type
        // - id     : the part of the ean that identifies something
        // - value  : if the id encodes a numerical value, it will be put there
        // - unit   : if the encoded value has a unit, it will be put there. 
        //            not to be confused with the 'unit' type, which represent an unit of a 
        //            unique product
        // - base_code : the ean code with all the encoding parts set to zero; the one put on
        //               the product in the backend

        parse_ean: function(ean){
            var parse_result = {
                encoding: 'ean13',
                type:'unknown',  
                prefix:'',
                code:ean,
                base_code: ean,
                id:'',
                value: 0,
                unit: 'none',
            };

            function match_prefix(prefix_set, type){
                for(prefix in prefix_set){
                    if(ean.substring(0,prefix.length) === prefix){
                        parse_result.prefix = prefix;
                        parse_result.type = type;
                        return true;
                    }
                }
                return false;
            }

            if (!this.check_ean(ean)){
                parse_result.type = 'error';
            } else if( match_prefix(this.price_prefix_set,'price')){
                parse_result.id = ean.substring(0,7);
                parse_result.base_code = this.sanitize_ean(ean.substring(0,7));
                parse_result.value = Number(ean.substring(7,12))/100.0;
                parse_result.unit  = 'euro';
            } else if( match_prefix(this.weight_prefix_set,'weight')){
                parse_result.id = ean.substring(0,7);
                parse_result.value = Number(ean.substring(7,12))/1000.0;
                parse_result.base_code = this.sanitize_ean(ean.substring(0,7));
                parse_result.unit = 'Kg';
            } else if( match_prefix(this.client_prefix_set,'client')){
                parse_result.id = ean.substring(0,7);
                parse_result.unit = 'Kg';
            } else if( match_prefix(this.cashier_prefix_set,'cashier')){
                parse_result.id = ean.substring(0,7);
            } else if( match_prefix(this.discount_prefix_set,'discount')){
                parse_result.id    = ean.substring(0,7);
                parse_result.base_code = this.sanitize_ean(ean.substring(0,7));
                parse_result.value = Number(ean.substring(7,12))/100.0;
                parse_result.unit  = '%';
            } else {
                parse_result.type = 'unit';
                parse_result.prefix = '';
                parse_result.id = ean;
            }
            return parse_result;
        },
        
        scan: function(code){
            if(code.length < 3){
                return;
            }else if(code.length === 13 && this.check_ean(code)){
                var parse_result = this.parse_ean(code);
            }else if(code.length === 12 && this.check_ean('0'+code)){
                // many barcode scanners strip the leading zero of ean13 barcodes.
                // This is because ean-13 are UCP-A with an additional zero at the beginning,
                // so by stripping zeros you get retrocompatibility with UCP-A systems.
                var parse_result = this.parse_ean('0'+code);
            }else if(this.pos.db.get_product_by_reference(code)){
                var parse_result = {
                    encoding: 'reference',
                    type: 'unit',
                    code: code,
                    prefix: '',
                };
            }else{
                var parse_result = {
                    encoding: 'error',
                    type: 'error',
                    code: code,
                    prefix: '',
                };
                return;
            }

            if(parse_result.type in {'unit':'', 'weight':'', 'price':''}){    //ean is associated to a product
                if(this.action_callback['product']){
                    this.action_callback['product'](parse_result);
                }
            }else{
                if(this.action_callback[parse_result.type]){
                    this.action_callback[parse_result.type](parse_result);
                }
            }
        },

        // starts catching keyboard events and tries to interpret codebar 
        // calling the callbacks when needed.
        connect: function(){

            var self = this;
            var code = "";
            var timeStamp  = 0;
            var onlynumbers = true;
            var timeout = null;

            this.handler = function(e){

                if(e.which === 13){ //ignore returns
                    e.preventDefault();
                    return;
                }

                if(timeStamp + 50 < new Date().getTime()){
                    code = "";
                    onlynumbers = true;
                }

                timeStamp = new Date().getTime();
                clearTimeout(timeout);

                if( e.which < 48 || e.which >= 58 ){ // not a number
                    onlynumbers = false;
                }

                code += String.fromCharCode(e.which);

                // we wait for a while after the last input to be sure that we are not mistakingly
                // returning a code which is a prefix of a bigger one :
                // Internal Ref 5449 vs EAN13 5449000...

                timeout = setTimeout(function(){
                    self.scan(code);
                    code = "";
                    onlynumbers = true;
                },100);
            };

            $('body').on('keypress', this.handler);
        },

        // stops catching keyboard events 
        disconnect: function(){
            $('body').off('keypress', this.handler)
        },

        // the barcode scanner will listen on the hw_proxy/scanner interface for 
        // scan events until disconnect_from_proxy is called
        connect_to_proxy: function(){ 
            var self = this;
            this.remote_scanning = true;
            if(this.remote_active >= 1){
                return;
            }
            this.remote_active = 1;

            function waitforbarcode(){
                return self.proxy.connection.rpc('/hw_proxy/scanner',{},{timeout:7500})
                    .then(function(barcode){
                        if(!self.remote_scanning){ 
                            self.remote_active = 0;
                            return; 
                        }
                        self.scan(barcode);
                        waitforbarcode();
                    },
                    function(){
                        if(!self.remote_scanning){
                            self.remote_active = 0;
                            return;
                        }
                        setTimeout(waitforbarcode,5000);
                    });
            }
            waitforbarcode();
        },

        // the barcode scanner will stop listening on the hw_proxy/scanner remote interface
        disconnect_from_proxy: function(){
            this.remote_scanning = false;
        },
    });

}
