odoo.define('pos_restaurant.floors', function (require) {
"use strict";

var { PosGlobalState, Order, Payment } = require('point_of_sale.models');
const { Gui } = require('point_of_sale.Gui');
const Registries = require('point_of_sale.Registries');


// New orders are now associated with the current table, if any.
const PosRestaurantOrder = (Order) => class PosRestaurantOrder extends Order {
    constructor(obj, options) {
        super(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (this.pos.config.iface_floorplan && !this.table && !options.json) {
                this.table = this.pos.table;
            }
            this.customer_count = this.customer_count || 1;
        }
    }
    export_as_JSON() {
        var json = super.export_as_JSON(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (this.pos.config.iface_floorplan) {
                json.table = this.table ? this.table.name : undefined;
                json.table_id = this.table ? this.table.id : false;
                json.floor = this.table ? this.table.floor.name : false;
                json.floor_id = this.table ? this.table.floor.id : false;
            }
            json.customer_count = this.customer_count;
        }
        return json;
    }
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (this.pos.config.iface_floorplan) {
                this.table = this.pos.tables_by_id[json.table_id];
                this.floor = this.table ? this.pos.floors_by_id[json.floor_id] : undefined;
            }
            this.customer_count = json.customer_count;
        }
    }
    export_for_printing() {
        var json = super.export_for_printing(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            if (this.pos.config.iface_floorplan) {
                json.table = this.table ? this.table.name : undefined;
                json.floor = this.table ? this.table.floor.name : undefined;
            }
            json.customer_count = this.get_customer_count();
        }
        return json;
    }
    get_customer_count(){
        return this.customer_count;
    }
    set_customer_count(count) {
        this.customer_count = Math.max(count,0);
    }
}
Registries.Model.extend(Order, PosRestaurantOrder);

// We need to change the way the regular UI sees the orders, it
// needs to only see the orders associated with the current table,
// and when an order is validated, it needs to go back to the floor map.
//
// And when we change the table, we must create an order for that table
// if there is none.
const PosRestaurantPosGlobalState = (PosGlobalState) => class PosRestaurantPosGlobalState extends PosGlobalState {
   async _processData(loadedData) {
       await super._processData(...arguments);
       if (this.config.is_table_management) {
           this.floors = loadedData['restaurant.floor'];
           this.loadRestaurantFloor();
       }
   }

    loadRestaurantFloor() {
       // we do this in the front end due to the circular/recursive reference needed
        // Ignore floorplan features if no floor specified.
        this.config.iface_floorplan = !!(this.floors && this.floors.length > 0);
        if (this.config.iface_floorplan) {
            this.floors_by_id = {};
            this.tables_by_id = {};
            for (let floor of this.floors) {
                this.floors_by_id[floor.id] = floor;
                for (let table of floor.tables) {
                    this.tables_by_id[table.id] = table;
                    table.floor = floor;
                }
            }
        }
    }

    async after_load_server_data() {
        var res = await super.after_load_server_data(...arguments);
        if (this.config.iface_floorplan) {
            this.table = null;
        }
        return res;
    }

    transfer_order_to_different_table () {
        this.order_to_transfer_to_different_table = this.get_order();

        // go to 'floors' screen, this will set the order to null and
        // eventually this will cause the gui to go to its
        // default_screen, which is 'floors'
        this.set_table(null);
    }

    remove_from_server_and_set_sync_state(ids_to_remove){
        var self = this;
        this.set_synch('connecting', ids_to_remove.length);
        return self._remove_from_server(ids_to_remove)
            .then(function(server_ids) {
                self.set_synch('connected');
            }).catch(function(reason){
                self.set_synch('error');
                throw reason;
            });
    }

    /**
     * Request the orders of the table with given id.
     * @param {number} table_id.
     * @param {dict} options.
     * @param {number} options.timeout optional timeout parameter for the rpc call.
     * @return {Promise}
     */
    _get_from_server (table_id, options) {
        options = options || {};
        var timeout = typeof options.timeout === 'number' ? options.timeout : 7500;
        return this.env.services.rpc({
                model: 'pos.order',
                method: 'get_table_draft_orders',
                args: [table_id],
                kwargs: {context: this.env.session.user_context},
            }, {
                timeout: timeout,
                shadow: false,
            })
    }

    transfer_order_to_table(table) {
        this.order_to_transfer_to_different_table.table = table;
        this.order_to_transfer_to_different_table.save_to_db();
    }

    push_order_for_transfer(order_ids, table_orders) {
        order_ids.push(this.order_to_transfer_to_different_table.uid);
        table_orders.push(this.order_to_transfer_to_different_table);
    }

    clean_table_transfer(table) {
        if (this.order_to_transfer_to_different_table && table) {
            this.order_to_transfer_to_different_table = null;
            return this.set_table(table);
        }
    }

    /**
     * Send cached orders to server
     * @param {object | null} table.
     * @param {array<models.Order>} table_orders.
     * @param {array<string>} order_ids (uid)
     * @return {void}
     * */
    sync_from_server(table, table_orders, order_ids) {
        var self = this;
        var ids_to_remove = this.db.get_ids_to_remove_from_server();
        var orders_to_sync = this.db.get_unpaid_orders_to_sync(order_ids);
        if (orders_to_sync.length) {
            this.set_synch('connecting', orders_to_sync.length);
            return this._save_to_server(orders_to_sync, {'draft': true}).then(function (server_ids) {
                server_ids.forEach(server_id => self.update_table_order(server_id, table_orders));
                if (!ids_to_remove.length) {
                    self.set_synch('connected');
                } else {
                    self.remove_from_server_and_set_sync_state(ids_to_remove);
                }
            }).catch(function(reason){
                self.set_synch('error');
            }).finally(function(){
                return self.clean_table_transfer(table);
            });
        } else {
            if (ids_to_remove.length) {
                self.remove_from_server_and_set_sync_state(ids_to_remove);
            }
            return self.clean_table_transfer(table);
        }
    }

    update_table_order(server_id, table_orders) {
        const order = table_orders.find(o => o.name === server_id.pos_reference);
        if (order) {
            order.server_id = server_id.id;
            order.save_to_db();
        }
        return order;
    }

    /**
     * @param {models.Order} order order to set
     */
    set_order_on_table(order) {
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
    }

    /**
     * Get table orders from server
     *
     * Warning: this replaces the cached orders with data fetched from server
     * If any cached fields did not make it to the server, their values will be lost.
     *
     * To avoid losing values of your new fields, you should do the following:
     * 1- Make sure your field exists on the related python model
     *
     * 2- Add your fields to the correct `pos.order._*_fields()` method returned dict
     * (item format: {python_name: ui_dict['js_name']})
     * (used for moving data from client to server)
     * // (a) `models.Order` => `pos.order._order_fields()`
     * // (b) `models.Orderline` => simply match the python name with the JS name
     * // (c) `models.Paymentline` => `pos.order._payment_fields()`
     *
     * 3- Add your fields to the correct `pos.order._get_fields_for_*()` method returned list
     * (used for moving data from server to client):
     * // (a) `models.Order` => `pos.order._get_fields_for_draft_order()`
     * // (b) `models.Orderline` => `pos.order._get_fields_for_order_line()`
     * // (c) `models.Paymentline` => `pos.order._get_fields_for_payment_lines()`
     *
     * 4- Set the value of the field to the model. This will trigger a cache update
     * (`export_as_JSON()` returned object will be stored).
     *
     * 5- If your setter could run in a time after `sync_from_server()` and before `sync_to_server()`
     * (e.g. in an event listener) make sure the setter itself calls
     * `sync_from_server()`.
     *
     * 6- Override `export_as_JSON()` of the model of your field
     * // function export_as_JSON() {
     * //     const json = _model_super.export_as_JSON.apply(this, arguments);
     * //     json.x = this.x;
     * //     return json;
     * // }
     *
     * 7- Override `init_from_JSON()` of the model of your field
     * // function init_from_JSON(json) {
     * //     _model_super.init_from_JSON.apply(this, arguments);
     * //     this.x = json.x;
     * // }
     * @param{object} table
     * @param{models.Order} order
     * */
    sync_to_server(table, order) {
        var self = this;
        var ids_to_remove = this.db.get_ids_to_remove_from_server();

        this.set_synch('connecting', 1);
        return this._get_from_server(table.id).then(function (server_orders) {
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
    }
    _replace_orders(orders_to_replace, new_orders) {
        var self = this;
        orders_to_replace.forEach(function(order){
            // We don't remove the validated orders because we still want to see them
            // in the ticket screen. Orders in 'ReceiptScreen' or 'TipScreen' are validated
            // orders.
            if (order.server_id && !order.finalized){
                self.orders.remove(order);
                order.destroy();
            }
        });
        new_orders.forEach(function(server_order){
            var new_order = self.createAutomaticallySavedOrder(server_order);
            self.orders.add(new_order);
        })
    }
    //@throw error
    async replace_table_orders_from_server(table) {
        const server_orders = await this._get_from_server(table.id);
        const orders = this.get_table_orders(table);
        this._replace_orders(orders, server_orders);
    }
    get_order_with_uid() {
        var order_ids = [];
        this.get_order_list().forEach(function(o){
            order_ids.push(o.uid);
        });

        return order_ids;
    }

    /**
     * Changes the current table.
     *
     * Switch table and make sure all nececery syncing tasks are done.
     * @param {object} table.
     * @param {models.Order|undefined} order if provided, set to this order
     */
    set_table(table, order) {
        let res = Promise.resolve();
        if(!table){
            res = this.sync_from_server(table, this.get_order_list(), this.get_order_with_uid());
            this.set_order(null);
            this.table = null;
        } else if (this.order_to_transfer_to_different_table) {
            var order_ids = this.get_order_with_uid();

            this.transfer_order_to_table(table);
            this.push_order_for_transfer(order_ids, this.get_order_list());

            res = this.sync_from_server(table, this.get_order_list(), order_ids);
        } else {
            this.table = table;
            res = this.sync_to_server(table, order);
        }
        return res;
    }

    // if we have tables, we do not load a default order, as the default order will be
    // set when the user selects a table.
    set_start_order() {
        if (!this.config.iface_floorplan) {
            super.set_start_order(...arguments);
        }
    }

    // we need to prevent the creation of orders when there is no
    // table selected.
    add_new_order() {
        if (this.config.iface_floorplan) {
            if (this.table) {
                return super.add_new_order(...arguments);
            } else {
                Gui.showPopup('ConfirmPopup', {
                    title: 'Unable to create order',
                    body: 'Orders cannot be created when there is no active table in restaurant mode',
                });
                return undefined;
            }
        } else {
            return super.add_new_order(...arguments);
        }
    }


    // get the list of unpaid orders (associated to the current table)
    get_order_list() {
        var orders = super.get_order_list(...arguments);
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
    }

    get_table_orders(table) {
        return this.orders.filter(o => o.table.id === table.id);
    }

    // get customer count at table
    get_customer_count(table) {
        var orders = this.get_table_orders(table).filter(order => !order.finalized);
        var count  = 0;
        for (var i = 0; i < orders.length; i++) {
            count += orders[i].get_customer_count();
        }
        return count;
    }

    // When we validate an order we go back to the floor plan.
    // When we cancel an order and there is multiple orders
    // on the table, stay on the table.
    on_removed_order(removed_order,index,reason){
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
            super.on_removed_order(...arguments);
        }
    }
}
Registries.Model.extend(PosGlobalState, PosRestaurantPosGlobalState);


const PosRestaurantPayment = (Payment) => class PosRestaurantPayment extends Payment {
    /**
     * Override this method to be able to show the 'Adjust Authorisation' button
     * on a validated payment_line and to show the tip screen which allow
     * tipping even after payment. By default, this returns true for all
     * non-cash payment.
     */
    canBeAdjusted() {
        if (this.payment_method.payment_terminal) {
            return this.payment_method.payment_terminal.canBeAdjusted(this.cid);
        }
        return !this.payment_method.is_cash_count;
    }
}
Registries.Model.extend(Payment, PosRestaurantPayment);

});
