
function openerp_pos_devices(instance,module){ //module is instance.point_of_sale

     var debug_devices = new (instance.web.Class.extend({
        active: false,
        payment_status: 'waiting_for_payment',
        weight: 0,
        activate: function(){
            this.active = true;
        },
        deactivate: function(){
            this.active = false;
        },
        set_weight: function(weight){ this.activate(); this.weight = weight; },
        accept_payment: function(){ this.activate(); this.payment_status = 'payment_accepted'; },
        reject_payment: function(){ this.activate(); this.payment_status = 'payment_rejected'; },
        delay_payment:  function(){ this.activate(); this.payment_status = 'waiting_for_payment'; },
    }))();

    //window.debug_devices = debug_devices;

    // this object interfaces with the local proxy to communicate to the various hardware devices
    // connected to the Point of Sale. As the communication only goes from the POS to the proxy,
    // methods are used both to signal an event, and to fetch information. 

    module.ProxyDevice  = instance.web.Class.extend({
        init: function(options){
            options = options || {};
            url = options.url || 'http://localhost:8069';
            
            this.weight = 0;
            this.weighting = false;

            this.paying = false;
            this.payment_status = 'waiting_for_payment';

            this.connection = new instance.web.JsonRPC();
            this.connection.setup(url);
            
        },
        message : function(name,params,success_callback, error_callback){
            success_callback = success_callback || function(){}; 
            error_callback   =  error_callback  || function(){};    

            if(debug_devices && debug_devices.active){
                console.log('PROXY:',name,params);
            }else{
                this.connection.rpc('/pos/'+name, params || {}, success_callback, error_callback);
            }
        },
        
        //a product has been scanned and recognized with success
        scan_item_success: function(){
            this.message('scan_item_success');
        },

        //a product has been scanned but not recognized
        scan_item_error_unrecognized: function(){
            this.message('scan_item_error_unrecognized');
        },

        //the client is asking for help
        help_needed: function(){
            this.message('help_needed');
        },

        //the client does not need help anymore
        help_canceled: function(){
            this.message('help_canceled');
        },

        //the client is starting to weight
        weighting_start: function(){
            this.weight = 0;
            if(debug_devices){
                debug_devices.weigth = 0;
            }
            this.weighting = true;
            this.message('weighting_start');
        },

        //returns the weight on the scale. 
        // is called at regular interval (up to 10x/sec) between a weighting_start()
        // and a weighting_end()
        weighting_read_kg: function(){
            var self = this;
            if(debug_devices && debug_devices.active){
                return debug_devices.weight;
            }else{
                this.message('weighting_read_kg',{},function(weight){
                    if(self.weighting){
                        self.weight = weight;
                    }
                });
                return self.weight;
            }
        },

        // the client has finished weighting products
        weighting_end: function(){
            this.weight = 0;
            this.weighting = false;
            this.message('weighting_end');
        },

        // the pos asks the client to pay 'price' units
        // method: 'mastercard' | 'cash' | ... ? TBD
        // info:   'extra information to display on the payment terminal' ... ? TBD
        payment_request: function(price, method, info){
            this.paying = true;
            this.payment_status = 'waiting_for_payment';
            if(debug_devices){
                debug_devices.payment_status = 'waiting_for_payment';
            }
            this.message('payment_request',{'price':price,'method':method,'info':info});
        },

        // is called at regular interval after a payment request to see if the client
        // has paid the required money
        // returns 'waiting_for_payment' | 'payment_accepted' | 'payment_rejected'
        is_payment_accepted: function(){
            var self = this;
            if(debug_devices.active){
                return debug_devices.payment_status;
            }else{
                this.message('is_payment_accepted', {}, function(payment_status){
                    if(self.paying){
                        self.payment_status = payment_status;
                    }
                });
                return self.payment_status;
            }
        },

        // the client cancels his payment
        payment_canceled: function(){
            this.paying = false;
            this.payment_status = 'waiting_for_payment';
            this.message('payment_canceled');
        },

        // called when the client logs in or starts to scan product
        transaction_start: function(){
            this.message('transaction_start');
        },

        // called when the clients has finished his interaction with the machine
        transaction_end: function(){
            this.message('transaction_end');
        },

        // called when the POS turns to cashier mode
        cashier_mode_activated: function(){
            this.message('cashier_mode_activated');
        },

        // called when the POS turns to client mode
        cashier_mode_deactivated: function(){
            this.message('cashier_mode_deactivated');
        },
        
        // ask for the cashbox (the physical box where you store the cash) to be opened
        open_cashbox: function(){
            this.message('open_cashbox');
        },

        /* ask the printer to print a receipt
         * receipt is a JSON object with the following specs:
         * receipt{
         *  - orderlines : list of orderlines :
         *     {
         *          quantity:           (number) the number of items, or the weight, 
         *          unit_name:          (string) the name of the item's unit (kg, dozen, ...)
         *          list_price:         (number) the price of one unit of the item before discount
         *          discount:           (number) the discount on the product in % [0,100] 
         *          product_name:       (string) the name of the product
         *          price_with_tax:     (number) the price paid for this orderline, tax included
         *          price_without_tax:  (number) the price paid for this orderline, without taxes
         *          tax:                (number) the price paid in taxes on this orderline
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
            this.message('print_receipt',{receipt: receipt});
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


        // returns true if the ean is a valid EAN codebar number by checking the control digit.
        // ean must be a string
        check_ean: function(ean){
            var code = ean.split('');
            for(var i = 0; i < code.length; i++){
                code[i] = Number(code[i]);
            }
            var st1 = code.slice();
            var st2 = st1.slice(0,st1.length-1).reverse();
            // some EAN13 barcodes have a length of 12, as they start by 0
            while (st2.length < 12) {
                st2.push(0);
            }
            var countSt3 = 1;
            var st3 = 0;
            $.each(st2, function() {
                if (countSt3%2 === 1) {
                    st3 +=  this;
                }
                countSt3 ++;
            });
            st3 *= 3;
            var st4 = 0;
            var countSt4 = 1;
            $.each(st2, function() {
                if (countSt4%2 === 0) {
                    st4 += this;
                }
                countSt4 ++;
            });
            var st5 = st3 + st4;
            var cd = (10 - (st5%10)) % 10;
            return code[code.length-1] === cd;
        },
        
        // attempts to interpret an ean (string encoding an ean)
        // it will check its validity then return an object containing various
        // information about the ean.
        // most importantly : 
        // - ean    : the ean
        // - type   : the type of the ean: 
        //      'price' |  'weight' | 'unit' | 'cashier' | 'client' | 'discount' | 'error'
        //
        // - prefix : the prefix that has ben used to determine the type
        // - id     : the part of the ean that identifies something
        // - value  : if the id encodes a numerical value, it will be put there
        // - unit   : if the encoded value has a unit, it will be put there. 
        //            not to be confused with the 'unit' type, which represent an unit of a 
        //            unique product

        parse_ean: function(ean){
            var parse_result = {
                type:'unknown', // 
                prefix:'',
                ean:ean,
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
                parse_result.value = Number(ean.substring(7,12))/100.0;
                parse_result.unit  = 'euro';
            } else if( match_prefix(this.weight_prefix_set,'weight')){
                parse_result.id = ean.substring(0,7);
                parse_result.value = Number(ean.substring(7,12))/1000.0;
                parse_result.unit = 'Kg';
            } else if( match_prefix(this.client_prefix_set,'client')){
                parse_result.id = ean.substring(0,7);
            } else if( match_prefix(this.cashier_prefix_set,'cashier')){
                parse_result.id = ean.substring(0,7);
            } else if( match_prefix(this.discount_prefix_set,'discount')){
                parse_result.id    = ean.substring(0,7);
                parse_result.value = Number(ean.substring(7,12))/100.0;
                parse_result.unit  = '%';
            } else {
                parse_result.type = 'unit';
                parse_result.prefix = '';
                parse_result.id = ean;
            }
            return parse_result;
        },

        // starts catching keyboard events and tries to interpret codebar 
        // calling the callbacks when needed.
        connect: function(){
            var self = this;
            var codeNumbers = [];
            var timeStamp = 0;
            var lastTimeStamp = 0;

            // The barcode readers acts as a keyboard, we catch all keyup events and try to find a 
            // barcode sequence in the typed keys, then act accordingly.
            $('body').delegate('','keyup', function (e){

                //We only care about numbers
                if (!isNaN(Number(String.fromCharCode(e.keyCode)))) {

                    // The barcode reader sends keystrokes with a specific interval.
                    // We look if the typed keys fit in the interval. 
                    if (codeNumbers.length==0) {
                        timeStamp = new Date().getTime();
                    } else {
                        if (lastTimeStamp + 30 < new Date().getTime()) {
                            // not a barcode reader
                            codeNumbers = [];
                            timeStamp = new Date().getTime();
                        }
                    }
                    codeNumbers.push(e.keyCode - 48);
                    lastTimeStamp = new Date().getTime();
                    if (codeNumbers.length == 13) {
                        //We have found what seems to be a valid codebar
                        var parse_result = self.parse_ean(codeNumbers.join(''));

                        if (parse_result.type === 'error') {    //most likely a checksum error, raise warning
                            console.error('ERROR: barcode checksum error:',parse_result);
                        }else if(parse_result.type in {'unit':'', 'weight':'', 'price':''}){    //ean is associated to a product
                            if(self.action_callback['product']){
                                self.action_callback['product'](parse_result);
                            }
                            //this.trigger("codebar",parse_result );
                        }else{
                            if(self.action_callback[parse_result.type]){
                                self.action_callback[parse_result.type](parse_result);
                            }
                        }

                        codeNumbers = [];
                    }
                } else {
                    // NaN
                    codeNumbers = [];
                }
            });
        },

        // stops catching keyboard events 
        disconnect: function(){
            $('body').undelegate('', 'keyup')
        },
    });

}
