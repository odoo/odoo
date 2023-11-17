/** @odoo-module */

/* The PosDB holds reference to data that is either
 * - static: does not change between pos reloads
 * - persistent : must stay between reloads ( orders )
 */

/**
 * cache the data in memory to avoid roundtrips to the localstorage
 *
 * NOTE/TODO: Originally, this is a prop of PosDB. However, if we keep it that way,
 * caching will result to infinite loop to calling the reactive callbacks.
 * Another way to solve the infinite loop is to move the instance of PosDB to env.
 * But I'm not sure if there is anything inside the object that needs to be observed,
 * so I guess this strategy is good enough for the moment.
 */
const CACHE = {};

export class PosDB {
    name = "openerp_pos_db"; //the prefix of the localstorage data
    limit = 100; // the maximum number of results returned by a search
    constructor(options) {
        options = options || {};
        this.name = options.name || this.name;
        this.limit = options.limit || this.limit;

        if (options.uuid) {
            this.name = this.name + "_" + options.uuid;
        }
    }

    /**
     * sets an uuid to prevent conflict in locally stored data between multiple PoS Configs. By
     * using the uuid of the config the local storage from other configs will not get effected nor
     * loaded in sessions that don't belong to them.
     *
     * @param {string} uuid Unique identifier of the PoS Config linked to the current session.
     */
    set_uuid(uuid) {
        this.name = this.name + "_" + uuid;
    }

    /* loads a record store from the database. returns default if nothing is found */
    load(store, deft) {
        if (CACHE[store] !== undefined) {
            return CACHE[store];
        }
        var data = localStorage[this.name + "_" + store];
        if (data !== undefined && data !== "") {
            data = JSON.parse(data);
            CACHE[store] = data;
            return data;
        } else {
            return deft;
        }
    }
    /* saves a record store to the database */
    save(store, data) {
        localStorage[this.name + "_" + store] = JSON.stringify(data);
        CACHE[store] = data;
    }
    /* paid orders */
    add_order(order) {
        var order_id = order.uid;
        var orders = this.load("orders", []);

        // if the order was already stored, we overwrite its data
        for (var i = 0, len = orders.length; i < len; i++) {
            if (orders[i].id === order_id) {
                orders[i].data = order;
                this.save("orders", orders);
                return order_id;
            }
        }

        // Only necessary when we store a new, validated order. Orders
        // that where already stored should already have been removed.
        this.remove_unpaid_order(order);

        orders.push({ id: order_id, data: order });
        this.save("orders", orders);
        return order_id;
    }
    remove_order(order_id) {
        var orders = this.load("orders", []);
        orders = orders.filter((order) => order.id !== order_id);
        this.save("orders", orders);
    }
    remove_all_orders() {
        this.save("orders", []);
    }
    get_orders() {
        return this.load("orders", []);
    }
    get_order(order_id) {
        var orders = this.get_orders();
        for (var i = 0, len = orders.length; i < len; i++) {
            if (orders[i].id === order_id) {
                return orders[i];
            }
        }
        return undefined;
    }

    /* working orders */
    save_unpaid_order(order) {
        var order_id = order.uid;
        var orders = this.load("unpaid_orders", []);
        var serialized = order.export_as_JSON();

        for (var i = 0; i < orders.length; i++) {
            if (orders[i].id === order_id) {
                orders[i].data = serialized;
                this.save("unpaid_orders", orders);
                return order_id;
            }
        }

        orders.push({ id: order_id, data: serialized });
        this.save("unpaid_orders", orders);
        return order_id;
    }
    remove_unpaid_order(order) {
        var orders = this.load("unpaid_orders", []);
        orders = orders.filter((o) => o.id !== order.uid);
        this.save("unpaid_orders", orders);
    }
    remove_all_unpaid_orders() {
        this.save("unpaid_orders", []);
    }
    get_unpaid_orders() {
        var saved = this.load("unpaid_orders", []);
        var orders = [];
        for (var i = 0; i < saved.length; i++) {
            orders.push(saved[i].data);
        }
        return orders;
    }
    /**
     * Return the orders with requested ids if they are unpaid.
     * @param {array<number>} ids order_ids.
     * @return {array<object>} list of orders.
     */
    get_unpaid_orders_to_sync(ids) {
        const savedOrders = this.load("unpaid_orders", []);
        return savedOrders.filter(
            (order) =>
                ids.includes(order.id) &&
                (order.data.server_id || order.data.lines.length || order.data.statement_ids.length)
        );
    }
    /**
     * Add a given order to the orders to be removed from the server.
     *
     * If an order is removed from a table it also has to be removed from the server to prevent it from reapearing
     * after syncing. This function will add the server_id of the order to a list of orders still to be removed.
     * @param {object} order object.
     */
    set_order_to_remove_from_server(order) {
        if (order.server_id === undefined) {
            return;
        }
        const to_remove = new Set(
            [this.load("unpaid_orders_to_remove", []), order.server_id].flat()
        );
        this.save("unpaid_orders_to_remove", [...to_remove]);
    }
    /**
     * Get a list of server_ids of orders to be removed.
     * @return {array<number>} list of server_ids.
     */
    get_ids_to_remove_from_server() {
        return this.load("unpaid_orders_to_remove", []);
    }
    /**
     * Remove server_ids from the list of orders to be removed.
     * @param {array<number>} ids
     */
    set_ids_removed_from_server(ids) {
        var to_remove = this.load("unpaid_orders_to_remove", []);

        to_remove = to_remove.filter((id) => !ids.includes(id));
        this.save("unpaid_orders_to_remove", to_remove);
    }
}
