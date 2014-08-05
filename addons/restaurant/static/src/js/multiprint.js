function openerp_restaurant_multiprint(instance,module){
    var QWeb = instance.web.qweb;
	var _t = instance.web._t;

    module.Printer = instance.web.Class.extend(openerp.PropertiesMixin,{
        init: function(parent,options){
            openerp.PropertiesMixin.init.call(this,parent);
            var self = this;
            options = options || {};
            var url = options.url || 'http://localhost:8069';
            this.connection = new instance.web.Session(undefined,url, { use_cors: true});
            this.host       = url;
            this.receipt_queue = [];
        },
        print: function(receipt){
            var self = this;
            if(receipt){
                this.receipt_queue.push(receipt);
            }
            var aborted = false;
            function send_printing_job(){
                if(self.receipt_queue.length > 0){
                    var r = self.receipt_queue.shift();
                    self.connection.rpc('/hw_proxy/print_xml_receipt',{receipt: r},{timeout: 5000})
                        .then(function(){
                            send_printing_job();
                        },function(){
                            self.receipt_queue.unshift(r);
                        });
                }
            }
            send_printing_job();
        },
    });

    module.PosModel.prototype.models.push({
        model: 'restaurant.printer',
        fields: ['name','proxy_ip','product_categories_ids'],
        domain: null,
        loaded: function(self,printers){
            var active_printers = {};
            for (var i = 0; i < self.config.printer_ids.length; i++) {
                active_printers[self.config.printer_ids[i]] = true;
            }

            self.printers = [];
            for(var i = 0; i < printers.length; i++){
                if(active_printers[printers[i].id]){
                    var printer = new module.Printer(self,{url:'http://'+printers[i].proxy_ip+':8069'});
                    printer.config = printers[i];
                    self.printers.push(printer);
                }
            }
        },
    });

    module.Order = module.Order.extend({
        lineResume: function(){
            var resume = {};
            this.get('orderLines').each(function(item){
                var line = item.export_as_JSON();
                if( typeof resume[line.product_id] === 'undefined'){
                    resume[line.product_id] = line.qty;
                }else{
                    resume[line.product_id] += line.qty;
                }
            });
            return resume;
        },
        saveChanges: function(){
            this.old_resume = this.lineResume();
        },
        computeChanges: function(categories){
            var current = this.lineResume();
            var old     = this.old_resume || {};
            var json    = this.export_as_JSON();
            var add = [];
            var rem = [];

            for( product in current){
                if (typeof old[product] === 'undefined'){
                    add.push({
                        'id': product,
                        'name': this.pos.db.get_product_by_id(product).name,
                        'quantity': current[product],
                    });
                }else if( old[product] < current[product]){
                    add.push({
                        'id': product,
                        'name': this.pos.db.get_product_by_id(product).name,
                        'quantity': current[product] - old[product],
                    });
                }else if( old[product] > current[product]){
                    rem.push({
                        'id': product,
                        'name': this.pos.db.get_product_by_id(product).name,
                        'quantity': old[product] - current[product],
                    });
                }
            }

            for( product in old){
                if(typeof current[product] === 'undefined'){
                    rem.push({
                        'id': product,
                        'name': this.pos.db.get_product_by_id(product).name,
                        'quantity': old[product], 
                    });
                }
            }

            if(categories && categories.length > 0){
                // filter the added and removed orders to only contains
                // products that belong to one of the categories supplied as a parameter

                var self = this;
                function product_in_category(product_id){
                    var cat = self.pos.db.get_product_by_id(product_id).pos_categ_id[0];
                    while(cat){
                        for(var i = 0; i < categories.length; i++){
                            if(cat === categories[i]){
                                return true;
                            }
                        }
                        cat = self.pos.db.get_category_parent_id(cat);
                    }
                    return false;
                }

                var _add = [];
                var _rem = [];
                
                for(var i = 0; i < add.length; i++){
                    if(product_in_category(add[i].id)){
                        _add.push(add[i]);
                    }
                }
                add = _add;

                for(var i = 0; i < rem.length; i++){
                    if(product_in_category(rem[i].id)){
                        _rem.push(rem[i]);
                    }
                }
                rem = _rem;
            }

            return {
                'new': add,
                'cancelled': rem,
                'table': json.table || 'unknown table',
                'name': json.name  || 'unknown order',
                'sequence_number': json.sequence_number || 0,
            };
            
        },
        printChanges: function(){
            var printers = this.pos.printers;
            for(var i = 0; i < printers.length; i++){
                var changes = this.computeChanges(printers[i].config.product_categories_ids);
                if ( changes['new'].length > 0 || changes['cancelled'].length > 0){
                    var receipt = QWeb.render('OrderChangeReceipt',{changes:changes, widget:this});
                    printers[i].print(receipt);
                }
            }
        },
        hasChangesToPrint: function(){
            var printers = this.pos.printers;
            for(var i = 0; i < printers.length; i++){
                var changes = this.computeChanges(printers[i].config.product_categories_ids);
                if ( changes['new'].length > 0 || changes['cancelled'].length > 0){
                    return true;
                }
            }
            return false;
        },
    });

    module.PosWidget.include({
        build_widgets: function(){
            var self = this;
            this._super();

            if(this.pos.printers.length){
                var submitorder = $(QWeb.render('SubmitOrderButton'));

                submitorder.click(function(){
                    var order = self.pos.get('selectedOrder');
                    if(order.hasChangesToPrint()){
                        order.printChanges();
                        order.saveChanges();
                        self.pos_widget.order_widget.update_summary();
                    }
                });
                
                submitorder.appendTo(this.$('.control-buttons'));
                this.$('.control-buttons').removeClass('oe_hidden');
            }
        },
        
    });

    module.OrderWidget.include({
        update_summary: function(){
            this._super();
            var order = this.pos.get('selectedOrder');

            if(order.hasChangesToPrint()){
                this.pos_widget.$('.order-submit').addClass('highlight');
            }else{
                this.pos_widget.$('.order-submit').removeClass('highlight');
            }
        },
    });

}
