odoo.define('pos_restaurant.multiprint', function (require) {
"use strict";

var { PosGlobalState, Orderline, Order } = require('point_of_sale.models');
var core = require('web.core');
var Printer = require('point_of_sale.Printer').Printer;
const Registries = require('point_of_sale.Registries');

var QWeb = core.qweb;


const PosResMultiprintPosGlobalState = (PosGlobalState) => class PosResMultiprintPosGlobalState extends PosGlobalState {
    async _processData(loadedData) {
        await super._processData(...arguments);
        if (this.config.module_pos_restaurant) {
            this._loadRestaurantPrinter(loadedData['restaurant.printer']);
        }
    }
    _loadRestaurantPrinter(printers) {
        this.unwatched.printers = [];
        // list of product categories that belong to one or more order printer
        this.printers_category_ids_set = new Set();
        for (let printerConfig of printers) {
            let printer = this.create_printer(printerConfig);
            printer.config = printerConfig;
            this.unwatched.printers.push(printer);
            for (let id of printer.config.product_categories_ids) {
                this.printers_category_ids_set.add(id);
            }
        }
        this.config.iface_printers = !!this.unwatched.printers.length;

    }
    create_printer(config) {
        var url = config.proxy_ip || '';
        if(url.indexOf('//') < 0) {
            url = window.location.protocol + '//' + url;
        }
        if(url.indexOf(':', url.indexOf('//') + 2) < 0 && window.location.protocol !== 'https:') {
            url = url + ':8069';
        }
        return new Printer(url, this);
    }
}
Registries.Model.extend(PosGlobalState, PosResMultiprintPosGlobalState);


const PosResMultiprintOrderline = (Orderline) => class PosResMultiprintOrderline extends Orderline {
    constructor() {
        super(...arguments);
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
    }
    // can this orderline be potentially printed ?
    printable() {
        return this.pos.db.is_product_in_category(this.pos.printers_category_ids_set, this.get_product().id);
    }
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.mp_dirty = json.mp_dirty;
        this.mp_skip  = json.mp_skip;
    }
    export_as_JSON() {
        var json = super.export_as_JSON(...arguments);
        json.mp_dirty = this.mp_dirty;
        json.mp_skip  = this.mp_skip;
        return json;
    }
    set_quantity(quantity) {
        if (this.pos.config.iface_printers && quantity !== this.quantity && this.printable()) {
            this.mp_dirty = true;
        }
        return super.set_quantity(...arguments);
    }
    can_be_merged_with(orderline) {
        return (!this.mp_skip) &&
               (!orderline.mp_skip) &&
               super.can_be_merged_with(...arguments);
    }
    set_skip(skip) {
        if (this.mp_dirty && skip && !this.mp_skip) {
            this.mp_skip = true;
        }
        if (this.mp_skip && !skip) {
            this.mp_dirty = true;
            this.mp_skip  = false;
        }
    }
    set_dirty(dirty) {
        if (this.mp_dirty !== dirty) {
            this.mp_dirty = dirty;
        }
    }
    get_line_diff_hash(){
        if (this.get_note()) {
            return this.id + '|' + this.get_note();
        } else {
            return '' + this.id;
        }
    }
}
Registries.Model.extend(Orderline, PosResMultiprintOrderline);


const PosResMultiprintOrder = (Order) => class PosResMultiprintOrder extends Order {
    build_line_resume(){
        var resume = {};
        this.orderlines.forEach(function(line){
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
    }
    saveChanges(){
        this.saved_resume = this.build_line_resume();
        this.orderlines.forEach(function(line){
            line.set_dirty(false);
        });
        // We sync if the caller is not the current order.
        // Otherwise, cached "changes" fields (mp_dirty, saved_resume)
        // will be invalidated without reaching the server
        const isTheCurrentOrder = this.pos.get_order() && this.pos.get_order().uid === this.uid;
        if (!isTheCurrentOrder && this.server_id) {
            // Save to cache first so that the saved_resume is up-to-date.
            this.save_to_db();
            this.pos.sync_from_server(null, [this], [this.uid]);
        }
    }
    computeChanges(categories){
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

    }
    async printChanges(){
        var printers = this.pos.unwatched.printers;
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
    }
    hasChangesToPrint(){
        var printers = this.pos.unwatched.printers;
        for(var i = 0; i < printers.length; i++){
            var changes = this.computeChanges(printers[i].config.product_categories_ids);
            if ( changes['new'].length > 0 || changes['cancelled'].length > 0){
                return true;
            }
        }
        return false;
    }
    hasSkippedChanges() {
        var orderlines = this.get_orderlines();
        for (var i = 0; i < orderlines.length; i++) {
            if (orderlines[i].mp_skip) {
                return true;
            }
        }
        return false;
    }
    export_as_JSON(){
        var json = super.export_as_JSON(...arguments);
        json.multiprint_resume = JSON.stringify(this.saved_resume);
        return json;
    }
    init_from_JSON(json){
        super.init_from_JSON(...arguments);
        this.saved_resume = json.multiprint_resume && JSON.parse(json.multiprint_resume);
    }
}
Registries.Model.extend(Order, PosResMultiprintOrder);


});
