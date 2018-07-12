odoo.define('pos_restaurant.multiprint', function (require) {
"use strict";

var models = require('point_of_sale.models');
var screens = require('point_of_sale.screens');
var core = require('web.core');
var mixins = require('web.mixins');
var Session = require('web.Session');

var QWeb = core.qweb;

var Printer = core.Class.extend(mixins.PropertiesMixin,{
    init: function(parent,options){
        mixins.PropertiesMixin.init.call(this);
        this.setParent(parent);
        options = options || {};
        var url = options.url || 'http://localhost:8069';
        this.connection = new Session(undefined,url, { use_cors: true});
        this.host       = url;
        this.receipt_queue = [];
    },
    print: function(receipt){
        var self = this;
        if(receipt){
            this.receipt_queue.push(receipt);
        }
        function send_printing_job(){
            if(self.receipt_queue.length > 0){
                var r = self.receipt_queue.shift();
                var options = {shadow: true, timeout: 5000};
                self.connection.rpc('/hw_proxy/print_xml_receipt', {receipt: r}, options)
                    .then(function(){
                        send_printing_job();
                    },function(error, event){
                        self.receipt_queue.unshift(r);
                        console.log('There was an error while trying to print the order:');
                        console.log(error);
                    });
            }
        }
        send_printing_job();
    },
});

models.load_models({
    model: 'restaurant.printer',
    fields: ['name','proxy_ip','product_categories_ids'],
    domain: null,
    loaded: function(self,printers){
        var active_printers = {};
        for (var i = 0; i < self.config.printer_ids.length; i++) {
            active_printers[self.config.printer_ids[i]] = true;
        }

        self.printers = [];
        self.printers_categories = {}; // list of product categories that belong to
                                       // one or more order printer

        for(var i = 0; i < printers.length; i++){
            if(active_printers[printers[i].id]){
                var url = printers[i].proxy_ip || '';
                if(url.indexOf('//') < 0){
                    url = 'http://'+url;
                }
                if(url.indexOf(':',url.indexOf('//')+2) < 0){
                    url = url+':8069';
                }
                var printer = new Printer(self,{url:url});
                printer.config = printers[i];
                self.printers.push(printer);

                for (var j = 0; j < printer.config.product_categories_ids.length; j++) {
                    self.printers_categories[printer.config.product_categories_ids[j]] = true;
                }
            }
        }
        self.printers_categories = _.keys(self.printers_categories);
        self.config.iface_printers = !!self.printers.length;
    },
});

var _super_orderline = models.Orderline.prototype;

models.Orderline = models.Orderline.extend({
    initialize: function() {
        _super_orderline.initialize.apply(this,arguments);
        if (!this.pos.config.iface_printers) {
            return;
        }
        if (typeof this.mp_dirty === 'undefined') {
            // mp dirty is true if this orderline has changed
            // since the last kitchen print
            // it's left undefined if the orderline does not
            // need to be printed to a printer. 

            this.mp_dirty = this.printable() || undefined;
        } 
        if (!this.mp_skip) {
            // mp_skip is true if the cashier want this orderline
            // not to be sent to the kitchen
            this.mp_skip  = false;
        }
    },
    // can this orderline be potentially printed ? 
    printable: function() {
        return this.pos.db.is_product_in_category(this.pos.printers_categories, this.get_product().id);
    },
    init_from_JSON: function(json) {
        _super_orderline.init_from_JSON.apply(this,arguments);
        this.mp_dirty = json.mp_dirty;
        this.mp_skip  = json.mp_skip;
    },
    export_as_JSON: function() {
        var json = _super_orderline.export_as_JSON.apply(this,arguments);
        json.mp_dirty = this.mp_dirty;
        json.mp_skip  = this.mp_skip;
        return json;
    },
    set_quantity: function(quantity) {
        if (this.pos.config.iface_printers && quantity !== this.quantity && this.printable()) {
            this.mp_dirty = true;
        }
        _super_orderline.set_quantity.apply(this,arguments);
    },
    can_be_merged_with: function(orderline) { 
        return (!this.mp_skip) && 
               (!orderline.mp_skip) &&
               _super_orderline.can_be_merged_with.apply(this,arguments);
    },
    set_skip: function(skip) {
        if (this.mp_dirty && skip && !this.mp_skip) {
            this.mp_skip = true;
            this.trigger('change',this);
        }
        if (this.mp_skip && !skip) {
            this.mp_dirty = true;
            this.mp_skip  = false;
            this.trigger('change',this);
        }
    },
    set_dirty: function(dirty) {
        this.mp_dirty = dirty;
        this.trigger('change',this);
    },
    get_line_diff_hash: function(){
        if (this.get_note()) {
            return this.id + '|' + this.get_note();
        } else {
            return '' + this.id;
        }
    },
});

screens.OrderWidget.include({
    render_orderline: function(orderline) {
        var node = this._super(orderline);
        if (this.pos.config.iface_printers) {
            if (orderline.mp_skip) {
                node.classList.add('skip');
            } else if (orderline.mp_dirty) {
                node.classList.add('dirty');
            }
        }
        return node;
    },
    click_line: function(line, event) {
        if (!this.pos.config.iface_printers) {
            this._super(line, event);
        } else if (this.pos.get_order().selected_orderline !== line) {
            this.mp_dbclk_time = (new Date()).getTime();
        } else if (!this.mp_dbclk_time) {
            this.mp_dbclk_time = (new Date()).getTime();
        } else if (this.mp_dbclk_time + 500 > (new Date()).getTime()) {
            line.set_skip(!line.mp_skip);
            this.mp_dbclk_time = 0;
        } else {
            this.mp_dbclk_time = (new Date()).getTime();
        }

        this._super(line, event);
    },
});

var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    build_line_resume: function(){
        var resume = {};
        this.orderlines.each(function(line){
            if (line.mp_skip) {
                return;
            }
            var line_hash = line.get_line_diff_hash();
            var qty  = Number(line.get_quantity());
            var note = line.get_note();
            var product_id = line.get_product().id;

            if (typeof resume[line_hash] === 'undefined') {
                resume[line_hash] = {
                    qty: qty,
                    note: note,
                    product_id: product_id,
                    product_name_wrapped: line.generate_wrapped_product_name(),
                };
            } else {
                resume[line_hash].qty += qty;
            }

        });
        return resume;
    },
    saveChanges: function(){
        this.saved_resume = this.build_line_resume();
        this.orderlines.each(function(line){
            line.set_dirty(false);
        });
        this.trigger('change',this);
    },
    computeChanges: function(categories){
        var current_res = this.build_line_resume();
        var old_res     = this.saved_resume || {};
        var json        = this.export_as_JSON();
        var add = [];
        var rem = [];
        var line_hash;

        for ( line_hash in current_res) {
            var curr = current_res[line_hash];
            var old  = old_res[line_hash];

            if (typeof old === 'undefined') {
                add.push({
                    'id':       curr.product_id,
                    'name':     this.pos.db.get_product_by_id(curr.product_id).display_name,
                    'name_wrapped': curr.product_name_wrapped,
                    'note':     curr.note,
                    'qty':      curr.qty,
                });
            } else if (old.qty < curr.qty) {
                add.push({
                    'id':       curr.product_id,
                    'name':     this.pos.db.get_product_by_id(curr.product_id).display_name,
                    'name_wrapped': curr.product_name_wrapped,
                    'note':     curr.note,
                    'qty':      curr.qty - old.qty,
                });
            } else if (old.qty > curr.qty) {
                rem.push({
                    'id':       curr.product_id,
                    'name':     this.pos.db.get_product_by_id(curr.product_id).display_name,
                    'name_wrapped': curr.product_name_wrapped,
                    'note':     curr.note,
                    'qty':      old.qty - curr.qty,
                });
            }
        }

        for (line_hash in old_res) {
            if (typeof current_res[line_hash] === 'undefined') {
                var old = old_res[line_hash];
                rem.push({
                    'id':       old.product_id,
                    'name':     this.pos.db.get_product_by_id(old.product_id).display_name,
                    'name_wrapped': old.product_name_wrapped,
                    'note':     old.note,
                    'qty':      old.qty, 
                });
            }
        }

        if(categories && categories.length > 0){
            // filter the added and removed orders to only contains
            // products that belong to one of the categories supplied as a parameter

            var self = this;

            var _add = [];
            var _rem = [];
            
            for(var i = 0; i < add.length; i++){
                if(self.pos.db.is_product_in_category(categories,add[i].id)){
                    _add.push(add[i]);
                }
            }
            add = _add;

            for(var i = 0; i < rem.length; i++){
                if(self.pos.db.is_product_in_category(categories,rem[i].id)){
                    _rem.push(rem[i]);
                }
            }
            rem = _rem;
        }

        var d = new Date();
        var hours   = '' + d.getHours();
            hours   = hours.length < 2 ? ('0' + hours) : hours;
        var minutes = '' + d.getMinutes();
            minutes = minutes.length < 2 ? ('0' + minutes) : minutes;

        return {
            'new': add,
            'cancelled': rem,
            'table': json.table || false,
            'floor': json.floor || false,
            'name': json.name  || 'unknown order',
            'time': {
                'hours':   hours,
                'minutes': minutes,
            },
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
    hasSkippedChanges: function() {
        var orderlines = this.get_orderlines();
        for (var i = 0; i < orderlines.length; i++) {
            if (orderlines[i].mp_skip) {
                return true;
            }
        }
        return false;
    },
    export_as_JSON: function(){
        var json = _super_order.export_as_JSON.apply(this,arguments);
        json.multiprint_resume = this.saved_resume;
        return json;
    },
    init_from_JSON: function(json){
        _super_order.init_from_JSON.apply(this,arguments);
        this.saved_resume = json.multiprint_resume;
    },
});

var SubmitOrderButton = screens.ActionButtonWidget.extend({
    'template': 'SubmitOrderButton',
    button_click: function(){
        var order = this.pos.get_order();
        if(order.hasChangesToPrint()){
            order.printChanges();
            order.saveChanges();
        }
    },
});

screens.define_action_button({
    'name': 'submit_order',
    'widget': SubmitOrderButton,
    'condition': function() {
        return this.pos.printers.length;
    },
});

screens.OrderWidget.include({
    update_summary: function(){
        this._super();
        var changes = this.pos.get_order().hasChangesToPrint();
        var skipped = changes ? false : this.pos.get_order().hasSkippedChanges();
        var buttons = this.getParent().action_buttons;

        if (buttons && buttons.submit_order) {
            buttons.submit_order.highlight(changes);
            buttons.submit_order.altlight(skipped);
        }
    },
});

});
