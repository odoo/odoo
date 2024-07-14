/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order } from "@point_of_sale/app/store/models";
import { uuidv4 } from "@point_of_sale/utils";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    isRestaurantCountryGermanyAndFiskaly() {
        return this.isCountryGermanyAndFiskaly() && this.config.module_pos_restaurant;
    },
    //@Override
    disallowLineQuantityChange() {
        const result = super.disallowLineQuantityChange(...arguments);
        return this.isRestaurantCountryGermanyAndFiskaly() || result;
    },
    //@Override
    _updateOrder(orderResponseData, tableOrders) {
        const order = super._updateOrder(...arguments);
        if (this.isRestaurantCountryGermanyAndFiskaly() && orderResponseData.differences && order) {
            order.createAndFinishOrderTransaction(orderResponseData.differences);
        }
        return order;
    },
    //@Override
    _postRemoveFromServer(serverIds, data) {
        if (this.isRestaurantCountryGermanyAndFiskaly() && data.length > 0) {
            // at this point of the flow, it's impossible to retrieve the local order, only the ids were stored
            // therefore we create an "empty" order object in order to call the needed methods
            data.forEach(async (elem) => {
                const order = new Order({ env: this.env }, { pos: this });
                await order.cancelOrderTransaction(elem.differences);
            });
        }
        return super._postRemoveFromServer(...arguments);
    },
    //@Override
    /**
     * We first have to send the line items to Fiskaly from the orders offline queue
     */
    async _flush_orders(orders, options) {
        if (!this.isRestaurantCountryGermanyAndFiskaly()) {
            return super._flush_orders(...arguments);
        }
        if (!orders || !orders.length) {
            return Promise.resolve([]);
        }
        const ordersCheckDifference = orders
            .filter((elem) => !elem.data.fiskaly_lines_sent)
            .map((elem) => elem.data);
        let differences = {};
        if (ordersCheckDifference.length > 0) {
            try {
                differences = await this.env.services.orm.call(
                    "pos.order",
                    "retrieve_line_difference",
                    [ordersCheckDifference]
                );
            } catch (error) {
                this.set_synch("disconnected");
                throw error;
            }
        }

        let fiskalyError;
        if (Object.keys(differences).length > 0) {
            const ordersToUpdate = {};
            for (const orderJsonData of ordersCheckDifference) {
                if (!fiskalyError && differences[orderJsonData.uid].length > 0) {
                    const order = new Order({ env: this.env }, { pos: this, json: orderJsonData });
                    try {
                        await order.sendLineDifference(differences[orderJsonData.uid]);
                        ordersToUpdate[orderJsonData.uid] = order.export_as_JSON();
                    } catch (error) {
                        fiskalyError = error;
                    }
                }
            }
            if (Object.keys(ordersToUpdate).length > 0) {
                for (const order of orders) {
                    if (ordersToUpdate[order.data.uid]) {
                        order.data = ordersToUpdate[order.data.uid];
                    }
                }
                this.db.save("orders", orders);
            }
            if (fiskalyError) {
                this.set_synch("disconnected");
                fiskalyError.code = "fiskaly";
                throw fiskalyError;
            }
        }

        return super._flush_orders(...arguments);
    },
});

patch(Order.prototype, {
    // @Override
    setup() {
        super.setup(...arguments);
        if (this.pos.isRestaurantCountryGermanyAndFiskaly()) {
            this.fiskalyLinesSent = false; // this is mainly used for offline scenario
            this.save_to_db();
        }
    },
    //@Override
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (this.pos.isRestaurantCountryGermanyAndFiskaly()) {
            json["fiskaly_lines_sent"] = this.fiskalyLinesSent;
        }
        return json;
    },
    //@Override
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        if (this.pos.isRestaurantCountryGermanyAndFiskaly()) {
            this.fiskalyLinesSent = json.fiskaly_lines_sent;
        }
    },
    _updateTimeStart(seconds) {
        if (
            !(
                this.pos.isRestaurantCountryGermanyAndFiskaly() &&
                this.tssInformation.time_start.value
            )
        ) {
            super._updateTimeStart(...arguments);
        }
    },
    async createAndFinishOrderTransaction(lineDifference) {
        const transactionUuid = uuidv4();
        if (!this.pos.getApiToken()) {
            await this._authenticate();
        }

        lineDifference.forEach((line) => {
            line.quantity = line.quantity.toString(); // Fiskaly ask this to be a string
            line.price_per_unit = this.env.utils.roundCurrency(line.price_per_unit).toFixed(2);
        });
        const data = {
            state: "ACTIVE",
            client_id: this.pos.getClientId(),
        };
        return $.ajax({
            url: `${this.pos.getApiUrl()}/tss/${this.pos.getTssId()}/tx/${transactionUuid}${
                this.pos.isUsingApiV2() ? "?tx_revision=1" : ""
            }`,
            method: "PUT",
            headers: { Authorization: `Bearer ${this.pos.getApiToken()}` },
            data: JSON.stringify(data),
            contentType: "application/json",
            timeout: 5000,
        })
            .then(() => {
                const data = {
                    state: "FINISHED",
                    client_id: this.pos.getClientId(),
                    schema: {
                        standard_v1: {
                            order: {
                                line_items: lineDifference,
                            },
                        },
                    },
                };
                return $.ajax({
                    url: `${this.pos.getApiUrl()}/tss/${this.pos.getTssId()}/tx/${transactionUuid}?${
                        this.pos.isUsingApiV2() ? "tx_revision=2" : "last_revision=1"
                    }`,
                    method: "PUT",
                    headers: { Authorization: `Bearer ${this.pos.getApiToken()}` },
                    data: JSON.stringify(data),
                    contentType: "application/json",
                    timeout: 5000,
                });
            })
            .catch(async (error) => {
                if (error.status === 401) {
                    // Need to update the token
                    await this._authenticate();
                    return this.createAndFinishOrderTransaction(lineDifference);
                }
                // Return a Promise with rejected value for errors that are not handled here
                return Promise.reject(error);
            });
    },
    exportOrderLinesAsJson() {
        const orderLines = this.orderLines.map((item) => [0, 0, item.export_as_JSON()]);

        return {
            server_id: this.server_id ? this.server_id : false,
            uid: this.uid,
            lines: orderLines,
        };
    },
    async retrieveAndSendLineDifference() {
        await this.env.services.orm
            .call("pos.order", "retrieve_line_difference", [[this.exportOrderLinesAsJson()]])
            .then(async (data) => {
                if (data[this.uid].length > 0) {
                    await this.sendLineDifference(data[this.uid]);
                }
            });
    },
    async sendLineDifference(difference) {
        await this.createAndFinishOrderTransaction(difference);
        this.fiskalyLinesSent = true;
    },
    async cancelOrderTransaction(lineDifference) {
        if (lineDifference.length > 0) {
            await this.createAndFinishOrderTransaction(lineDifference);
        }
        await this.createTransaction();
        await this.cancelTransaction();
    },
});
