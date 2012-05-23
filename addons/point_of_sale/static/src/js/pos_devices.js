
function openerp_pos_devices(instance,module){ //module is instance.point_of_sale

    var QWeb = instance.web.qweb;   //TODO FIXME this should NOT be of any use in this file

    window.debug_devices = new (instance.web.Class.extend({
        payment_status: 'waiting_for_payment',
        weight: 0,
        accept_payment: function(){ this.payment_status = 'payment_accepted'; },
        reject_payment: function(){ this.payment_status = 'payment_rejected'; },
        delay_payment:  function(){ this.payment_status = 'waiting_for_payment'; },
    }))();

    // this object interfaces with the local proxy to communicate to the various hardware devices
    // connected to the Point of Sale. As the communication only goes from the POS to the proxy,
    // methods are used both to signal an event, and to fetch information. 

    module.ProxyDevice  = instance.web.Class.extend({
        init: function(options){
            options = options || {};
            url = options.url || 'http://localhost:8069';

            this.connection = new instance.web.JsonRPC();
            this.connection.setup(url);
        },
        message : function(name,params,callback){
            var success_callback = function(result){ console.log('PROXY SUCCESS:'+name+': ',result); }
            var error_callback = function(result){ console.log('PROXY ERROR:'+name+': ',result); }
            this.connection.rpc('/pos/'+name, params || {}, callback || success_callback, error_callback);
        },
        
        //a product has been scanned and recognized with success
        scan_item_success: function(){
            this.message('scan_item_success');
            console.log('PROXY: scan item success');
        },

        //a product has been scanned but not recognized
        scan_item_error_unrecognized: function(){
            this.message('scan_item_error_unrecognized');
            console.log('PROXY: scan item error');
        },

        //the client is asking for help
        help_needed: function(){
            this.message('help_needed');
            console.log('PROXY: help needed');
        },

        //the client does not need help anymore
        help_canceled: function(){
            this.message('help_canceled');
            console.log('PROXY: help canceled');
        },

        //the client is starting to weight
        weighting_start: function(){
            this.message('weighting_start');
            console.log('PROXY: weighting start');
        },

        //returns the weight on the scale. 
        // is called at regular interval (up to 10x/sec) between a weighting_start()
        // and a weighting_end()
        weighting_read_kg: function(){
            this.message('weighting_read_kg');
            console.log('PROXY: weighting read');
            //return Math.random() + 0.1;
            return window.debug_devices.weight;
        },

        // the client has finished weighting products
        weighting_end: function(){
            this.message('weighting_end');
            console.log('PROXY: weighting end');
        },

        // the pos asks the client to pay 'price' units
        // method: 'mastercard' | 'cash' | ... ? TBD
        // info:   'extra information to display on the payment terminal' ... ? TBD
        payment_request: function(price, method, info){
            this.message('payment_request',{'price':price,'method':method,'info':info});
            console.log('PROXY: payment request:',price,method,info);
        },

        // is called at regular interval after a payment request to see if the client
        // has paid the required money
        // returns 'waiting_for_payment' | 'payment_accepted' | 'payment_rejected'
        is_payment_accepted: function(){
            this.message('is_payment_accepted');
            console.log('PROXY: is payment accepted ?');
            //return 'waiting_for_payment'; // 'payment_accepted' | 'payment_rejected'
            return window.debug_devices.payment_status;
        },

        // the client cancels his payment
        payment_canceled: function(){
            this.message('payment_canceled');
            console.log('PROXY: payment canceled by client');
        },

        // called when the client logs in or starts to scan product
        transaction_start: function(){
            this.message('transaction_start');
            console.log('PROXY: transaction start');
        },

        // called when the clients has finished his interaction with the machine
        transaction_end: function(){
            this.message('transaction_end');
            console.log('PROXY: transaction end');
        },

        // called when the POS turns to cashier mode
        cashier_mode_activated: function(){
            this.message('cashier_mode_activated');
            console.log('PROXY: cashier mode activated');
        },

        // called when the POS turns to client mode
        cashier_mode_deactivated: function(){
            this.message('cashier_mode_deactivated');
            console.log('PROXY: client mode activated');
        },
    });

    // this module interfaces with the barcode reader. It assumes the barcode reader
    // is set-up to act like  a keyboard. Use connect() and disconnect() to activate 
    // and deactivate the barcode reader. Use set_action_callbacks to tell it
    // what to do when it reads a barcode.
    module.BarcodeReader = instance.web.Class.extend({

        init: function(attributes){
            this.pos = attributes.pos;
            this.action_callback = {
                'product': undefined,   
                'cashier': undefined,
                'client':  undefined,
                'discount': undefined,
            };

            this.action_callback_stack = [];

            this.price_prefix_set = attributes.price_prefix_set     ||  {'02':'', '22':'', '24':'', '26':'', '28':''};
            this.weight_prefix_set = attributes.weight_prefix_set   ||  {'21':'','23':'','27':'','29':'','25':''};
            this.client_prefix_set = attributes.weight_prefix_set   ||  {'42':''};
            this.cashier_prefix_set = attributes.weight_prefix_set  ||  {'40':''};
            this.discount_prefix_set = attributes.weight_prefix_set ||  {'44':''};
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
    
        set_action_callbacks: function(callbacks){
            for(action in callbacks){
                this.action_callback[action] = callbacks[action];
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
            var prefix2 = ean.substring(0,2);

            if(!this.check_ean(ean)){
                parse_result.type = 'error';
            }else if (prefix2 in this.price_prefix_set){
                parse_result.type = 'price';
                parse_result.prefix = prefix2;
                parse_result.id = ean.substring(0,7);
                parse_result.value = Number(ean.substring(7,12))/100.0;
                parse_result.unit  = 'euro';
            } else if (prefix2 in this.weight_prefix_set){
                parse_result.type = 'weight';
                parse_result.prefix = prefix2;
                parse_result.id = ean.substring(0,7);
                parse_result.value = Number(ean.substring(7,12))/1000.0;
                parse_result.unit = 'Kg';
            }else if (prefix2 in this.client_prefix_set){
                parse_result.type = 'client';
                parse_result.prefix = prefix2;
                parse_result.id = ean.substring(0,7);
            }else if (prefix2 in this.cashier_prefix_set){
                parse_result.type = 'cashier';
                parse_result.prefix = prefix2;
                parse_result.id = ean.substring(0,7);
            }else if (prefix2 in this.discount_prefix_set){
                parse_result.type  = 'discount';
                parse_result.prefix = prefix2;
                parse_result.id    = ean.substring(0,7);
                parse_result.value = Number(ean.substring(7,12))/100.0;
                parse_result.unit  = '%';
            }else{
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
                        console.log('BARCODE:',parse_result);

                        if (parse_result.type === 'error') {    //most likely a checksum error, raise warning
                            $(QWeb.render('pos-scan-warning')).dialog({
                                resizable: false,
                                height:220,
                                modal: true,
                                title: "Warning",
                            });
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
