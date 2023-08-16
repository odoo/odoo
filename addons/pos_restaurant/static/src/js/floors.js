odoo.define('pos_restaurant.floors', function (require) {
"use strict";

var models = require('point_of_sale.models');
const { Gui } = require('point_of_sale.Gui');
const { posbus } = require('point_of_sale.utils');

// At POS Startup, load the floors, and add them to the pos model
models.load_models({
    model: 'restaurant.floor',
    fields: ['name','background_color','table_ids','sequence'],
    domain: function(self){ return [['pos_config_id','=',self.config.id]]; },
    loaded: function(self,floors){
        self.floors = floors;
        self.floors_by_id = {};
        for (var i = 0; i < floors.length; i++) {
            floors[i].tables = [];
            self.floors_by_id[floors[i].id] = floors[i];
        }

        // Make sure they display in the correct order
        self.floors = self.floors.sort(function(a,b){ return a.sequence - b.sequence; });

        // Ignore floorplan features if no floor specified.
        self.config.iface_floorplan = !!self.floors.length;
    },
});

// At POS Startup, after the floors are loaded, load the tables, and associate
// them with their floor.
models.load_models({
    model: 'restaurant.table',
    fields: ['name','width','height','position_h','position_v','shape','floor_id','color','seats'],
    loaded: function(self,tables){
        self.tables_by_id = {};
        for (var i = 0; i < tables.length; i++) {
            self.tables_by_id[tables[i].id] = tables[i];
            var floor = self.floors_by_id[tables[i].floor_id[0]];
            if (floor) {
                floor.tables.push(tables[i]);
                tables[i].floor = floor;
            }
        }
    },
});

// New orders are now associated with the current table, if any.
var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    initialize: function(attr,options) {
        _super_order.initialize.apply(this,arguments);
        if (!this.table && !options.json) {
            this.table = this.pos.table;
        }
        this.customer_count = this.customer_count || 1;
        this.save_to_db();
    },
    export_as_JSON: function() {
        var json = _super_order.export_as_JSON.apply(this,arguments);
        json.table     = this.table ? this.table.name : undefined;
        json.table_id  = this.table ? this.table.id : false;
        json.floor     = this.table ? this.table.floor.name : false;
        json.floor_id  = this.table ? this.table.floor.id : false;
        json.customer_count = this.customer_count;
        return json;
    },
    init_from_JSON: function(json) {
        _super_order.init_from_JSON.apply(this,arguments);
        this.table = this.pos.tables_by_id[json.table_id];
        this.floor = this.table ? this.pos.floors_by_id[json.floor_id] : undefined;
        this.customer_count = json.customer_count || 1;
    },
    export_for_printing: function() {
        var json = _super_order.export_for_printing.apply(this,arguments);
        json.table = this.table ? this.table.name : undefined;
        json.floor = this.table ? this.table.floor.name : undefined;
        json.customer_count = this.get_customer_count();
        return json;
    },
    get_customer_count: function(){
        return this.customer_count;
    },
    set_customer_count: function(count) {
        this.customer_count = Math.max(count,0);
        this.trigger('change');
    },
});

// We need to change the way the regular UI sees the orders, it
// needs to only see the orders associated with the current table,
// and when an order is validated, it needs to go back to the floor map.
//
// And when we change the table, we must create an order for that table
// if there is none.
var _super_posmodel = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    after_load_server_data: async function() {
        var res = await _super_posmodel.after_load_server_data.call(this);
        if (this.config.iface_floorplan) {
            this.table = null;
        }
        return res;
    },

    transfer_order_to_different_table: function () {
        this.order_to_transfer_to_different_table = this.get_order();

        // go to 'floors' screen, this will set the order to null and
        // eventually this will cause the gui to go to its
        // default_screen, which is 'floors'
        this.set_table(null);
    },

    remove_from_server_and_set_sync_state: function(ids_to_remove){
        var self = this;
        this.set_synch('connecting', ids_to_remove.length);
        return self._remove_from_server(ids_to_remove)
            .then(function(server_ids) {
                self.set_synch('connected');
            }).catch(function(reason){
                self.set_synch('error');
                throw reason;
            });
    },

    /**
     * Request the orders of the table with given id.
     * @param {number} table_id.
     * @param {dict} options.
     * @param {number} options.timeout optional timeout parameter for the rpc call.
     * @return {Promise}
     */
    _get_from_server: function (table_id, options) {
        options = options || {};
        var timeout = typeof options.timeout === 'number' ? options.timeout : 7500;
        return this.rpc({
                model: 'pos.order',
                method: 'get_table_draft_orders',
                args: [table_id],
                kwargs: {context: this.session.user_context},
            }, {
                timeout: timeout,
                shadow: false,
            })
    },

    transfer_order_to_table: function(table) {
        this.order_to_transfer_to_different_table.table = table;
        this.order_to_transfer_to_different_table.save_to_db();
    },

    push_order_for_transfer: function(order_ids, table_orders) {
        order_ids.push(this.order_to_transfer_to_different_table.uid);
        table_orders.push(this.order_to_transfer_to_different_table);
    },

    clean_table_transfer: function(table) {
        if (this.order_to_transfer_to_different_table && table) {
            this.order_to_transfer_to_different_table = null;
            this.set_table(table);
        }
    },

    sync_from_server: function(table, table_orders, order_ids) {
        var self = this;
        var ids_to_remove = this.db.get_ids_to_remove_from_server();
        var orders_to_sync = this.db.get_unpaid_orders_to_sync(order_ids);
        if (orders_to_sync.length) {
            this.set_synch('connecting', orders_to_sync.length);
            this._save_to_server(orders_to_sync, {'draft': true}).then(function (server_ids) {
                server_ids.forEach(server_id => self.update_table_order(server_id, table_orders));
                if (!ids_to_remove.length) {
                    self.set_synch('connected');
                } else {
                    self.remove_from_server_and_set_sync_state(ids_to_remove);
                }
            }).catch(function(reason){
                self.set_synch('error');
            }).finally(function(){
                self.clean_table_transfer(table);
            });
        } else {
            if (ids_to_remove.length) {
                self.remove_from_server_and_set_sync_state(ids_to_remove);
            }
            self.clean_table_transfer(table);
        }
    },

    update_table_order: function(server_id, table_orders) {
        const order = table_orders.find(o => o.name === server_id.pos_reference);
        if (order) {
            order.server_id = server_id.id;
            order.save_to_db();
        }
        return order;
    },

    /**
     * @param {models.Order} order order to set
     */
    set_order_on_table: function(order) {
        var orders = this.get_order_list();
        if (orders.length) {
            order = order ? orders.find((o) => o.uid === order.uid) : null;
            if (order) {
                this.set_order(order);
            } else {
                // do not mindlessly set the first order in the list.
                orders = orders.filter(order => !order.finalized);
                if (orders.length) {
                    this.set_order(orders[0]);
                } else {
                    this.add_new_order();
                }
            }
        } else {
            this.add_new_order();  // or create a new order with the current table
        }
    },

    sync_to_server: function(table, order) {
        var self = this;
        var ids_to_remove = this.db.get_ids_to_remove_from_server();

        this.set_synch('connecting', 1);
        this._get_from_server(table.id).then(function (server_orders) {
            var orders = self.get_order_list();
            self._replace_orders(orders, server_orders);
            if (!ids_to_remove.length) {
                self.set_synch('connected');
            } else {
                self.remove_from_server_and_set_sync_state(ids_to_remove);
            }
        }).catch(function(reason){
            self.set_synch('error');
        }).finally(function(){
            self.set_order_on_table(order);
        });
    },
    _replace_orders: function(orders_to_replace, new_orders) {
        var self = this;
        orders_to_replace.forEach(function(order){
            // We don't remove the validated orders because we still want to see them
            // in the ticket screen. Orders in 'ReceiptScreen' or 'TipScreen' are validated
            // orders.
            if (order.server_id && !order.finalized){
                self.get("orders").remove(order);
                order.destroy();
            }
        });
        new_orders.forEach(function(server_order){
            var new_order = new models.Order({},{pos: self, json: server_order});
            self.get("orders").add(new_order);
            new_order.save_to_db();
        });
    },
    //@throw error
    replace_table_orders_from_server: async function(table) {
        const server_orders = await this._get_from_server(table.id);
        const orders = this.get_table_orders(table);
        this._replace_orders(orders, server_orders);
    },
    get_order_with_uid: function() {
        var order_ids = [];
        this.get_order_list().forEach(function(o){
            order_ids.push(o.uid);
        });

        return order_ids;
    },

    /**
     * Changes the current table.
     *
     * Switch table and make sure all nececery syncing tasks are done.
     * @param {object} table.
     * @param {models.Order|undefined} order if provided, set to this order
     */
    set_table: function(table, order) {
        if(!table){
            this.sync_from_server(table, this.get_order_list(), this.get_order_with_uid());
            this.set_order(null);
            this.table = null;
        } else if (this.order_to_transfer_to_different_table) {
            var order_ids = this.get_order_with_uid();

            this.transfer_order_to_table(table);
            this.push_order_for_transfer(order_ids, this.get_order_list());

            this.sync_from_server(table, this.get_order_list(), order_ids);
            this.set_order(null);
        } else {
            this.table = table;
            this.sync_to_server(table, order);
        }
        posbus.trigger('table-set');
    },

    // if we have tables, we do not load a default order, as the default order will be
    // set when the user selects a table.
    set_start_order: function() {
        if (!this.config.iface_floorplan) {
            _super_posmodel.set_start_order.apply(this,arguments);
        }
    },

    // we need to prevent the creation of orders when there is no
    // table selected.
    add_new_order: function() {
        if (this.config.iface_floorplan) {
            if (this.table) {
                return _super_posmodel.add_new_order.apply(this, arguments);
            } else {
                Gui.showPopup('ConfirmPopup', {
                    title: 'Unable to create order',
                    body: 'Orders cannot be created when there is no active table in restaurant mode',
                });
                return undefined;
            }
        } else {
            return _super_posmodel.add_new_order.apply(this,arguments);
        }
    },


    // get the list of unpaid orders (associated to the current table)
    get_order_list: function() {
        var orders = _super_posmodel.get_order_list.call(this);
        if (!(this.config && this.config.iface_floorplan)) {
            return orders;
        } else if (!this.table) {
            return [];
        } else {
            var t_orders = [];
            for (var i = 0; i < orders.length; i++) {
                if ( orders[i].table === this.table) {
                    t_orders.push(orders[i]);
                }
            }
            return t_orders;
        }
    },

    // get the list of orders associated to a table. FIXME: should be O(1)
    get_table_orders: function(table) {
        var orders   = _super_posmodel.get_order_list.call(this);
        var t_orders = [];
        for (var i = 0; i < orders.length; i++) {
            if (orders[i].table === table) {
                t_orders.push(orders[i]);
            }
        }
        return t_orders;
    },

    // get customer count at table
    get_customer_count: function(table) {
        var orders = this.get_table_orders(table).filter(order => !order.finalized);
        var count  = 0;
        for (var i = 0; i < orders.length; i++) {
            count += orders[i].get_customer_count();
        }
        return count;
    },

    // When we validate an order we go back to the floor plan.
    // When we cancel an order and there is multiple orders
    // on the table, stay on the table.
    on_removed_order: function(removed_order,index,reason){
        if (this.config.iface_floorplan) {
            var order_list = this.get_order_list();
            if (reason === 'abandon') {
                this.db.set_order_to_remove_from_server(removed_order);
            }
            if( (reason === 'abandon' || removed_order.temporary) && order_list.length > 0){
                this.set_order(order_list[index] || order_list[order_list.length - 1], { silent: true });
            } else if (order_list.length === 0) {
                this.table ? this.set_order(null) : this.set_table(null);
            }
        } else {
            _super_posmodel.on_removed_order.apply(this,arguments);
        }
    },


});


var _super_paymentline = models.Paymentline.prototype;
models.Paymentline = models.Paymentline.extend({
    /**
     * Override this method to be able to show the 'Adjust Authorisation' button
     * on a validated payment_line and to show the tip screen which allow
     * tipping even after payment. By default, this returns true for all
     * non-cash payment.
     */
    canBeAdjusted: function() {
        if (this.payment_method.payment_terminal) {
            return this.payment_method.payment_terminal.canBeAdjusted(this.cid);
        }
        return !this.payment_method.is_cash_count;
    },
});

});
