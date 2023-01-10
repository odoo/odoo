odoo.define('pos_restaurant.multiprint', function (require) {
"use strict";

var models = require('point_of_sale.models');
var core = require('web.core');
var Printer = require('point_of_sale.Printer').Printer;

var QWeb = core.qweb;

models.PosModel = models.PosModel.extend({
    create_printer: function (config) {
        var url = config.proxy_ip || '';
        if(url.indexOf('//') < 0) {
            url = window.location.protocol + '//' + url;
        }
        if(url.indexOf(':', url.indexOf('//') + 2) < 0 && window.location.protocol !== 'https:') {
            url = url + ':8069';
        }
        return new Printer(url, this);
    },
});

models.load_models({
    model: 'restaurant.printer',
    fields: ['name','proxy_ip','product_categories_ids', 'printer_type'],
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
                var printer = self.create_printer(printers[i]);
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
        return _super_orderline.set_quantity.apply(this,arguments);
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
        if (this.mp_dirty !== dirty) {
            this.mp_dirty = dirty;
            this.trigger('change', this);
        }
    },
    get_line_diff_hash: function(){
        if (this.get_note()) {
            return this.id + '|' + this.get_note();
        } else {
            return '' + this.id;
        }
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
            var qty  = Number(line.get_quantity());
            var note = line.get_note();
            var product_id = line.get_product().id;
            var product_name = line.get_full_product_name();
            var p_key = product_id + " - " + product_name;
            var product_resume = p_key in resume ? resume[p_key] : {
                pid: product_id,
                product_name_wrapped: line.generate_wrapped_product_name(),
                qties: {},
            };
            if (note in product_resume['qties']) product_resume['qties'][note] += qty;
            else product_resume['qties'][note] = qty;
            resume[p_key] = product_resume;
        });
        return resume;
    },
    saveChanges: function(){
        this.saved_resume = this.build_line_resume();
        this.orderlines.each(function(line){
            line.set_dirty(false);
        });
        this.trigger('change',this);
        // We sync if the caller is not the current order.
        // Otherwise, cached "changes" fields (mp_dirty, saved_resume)
        // will be invalidated without reaching the server
        const isTheCurrentOrder = this.pos.get_order() && this.pos.get_order().uid === this.uid;
        if (!isTheCurrentOrder && this.server_id) {
            this.pos.sync_from_server(null, [this], [this.uid]);
        }
    },
    computeChanges: function(categories){
        var current_res = this.build_line_resume();
        var old_res     = this.saved_resume || {};
        var json        = this.export_as_JSON();
        var add = [];
        var rem = [];
        var p_key, note;

        for (p_key in current_res) {
            for (note in current_res[p_key]['qties']) {
                var curr = current_res[p_key];
                var old  = old_res[p_key] || {};
                var pid = curr.pid;
                var found = p_key in old_res && note in old_res[p_key]['qties'];

                if (!found) {
                    add.push({
                        'id':       pid,
                        'name':     this.pos.db.get_product_by_id(pid).display_name,
                        'name_wrapped': curr.product_name_wrapped,
                        'note':     note,
                        'qty':      curr['qties'][note],
                    });
                } else if (old['qties'][note] < curr['qties'][note]) {
                    add.push({
                        'id':       pid,
                        'name':     this.pos.db.get_product_by_id(pid).display_name,
                        'name_wrapped': curr.product_name_wrapped,
                        'note':     note,
                        'qty':      curr['qties'][note] - old['qties'][note],
                    });
                } else if (old['qties'][note] > curr['qties'][note]) {
                    rem.push({
                        'id':       pid,
                        'name':     this.pos.db.get_product_by_id(pid).display_name,
                        'name_wrapped': curr.product_name_wrapped,
                        'note':     note,
                        'qty':      old['qties'][note] - curr['qties'][note],
                    });
                }
            }
        }

        for (p_key in old_res) {
            for (note in old_res[p_key]['qties']) {
                var found = p_key in current_res && note in current_res[p_key]['qties'];
                if (!found) {
                    var old = old_res[p_key];
                    var pid = old.pid;
                    rem.push({
                        'id':       pid,
                        'name':     this.pos.db.get_product_by_id(pid).display_name,
                        'name_wrapped': old.product_name_wrapped,
                        'note':     note,
                        'qty':      old['qties'][note],
                    });
                }
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
    printChanges: async function(){
        var printers = this.pos.printers;
        let isPrintSuccessful = true;
        for(var i = 0; i < printers.length; i++){
            var changes = this.computeChanges(printers[i].config.product_categories_ids);
            if ( changes['new'].length > 0 || changes['cancelled'].length > 0){
                var receipt = QWeb.render('OrderChangeReceipt',{changes:changes, widget:this});
                const result = await printers[i].print_receipt(receipt);
                if (!result.successful) {
                    isPrintSuccessful = false;
                }
            }
        }
        return isPrintSuccessful;
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
        json.multiprint_resume = JSON.stringify(this.saved_resume);
        return json;
    },
    init_from_JSON: function(json){
        _super_order.init_from_JSON.apply(this,arguments);
        this.saved_resume = json.multiprint_resume && JSON.parse(json.multiprint_resume);
    },
});


});
