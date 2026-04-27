/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    //@Override
    setup() {
        super.setup(...arguments);
        if (this.pos.isCountryGermanyAndFiskaly()) {
            const _super_handlePushOrderError = this._handlePushOrderError.bind(this);
            this._handlePushOrderError = async (error) => {
                if (error.code === "fiskaly") {
                    this.pos.fiskalyError(error);
                } else {
                    _super_handlePushOrderError(error);
                }
            };
            this.validateOrderFree = true;
        }
    },
    //@override
    async validateOrder(isForceValidate) {
        if (this.pos.isCountryGermanyAndFiskaly() && !this.pos.data.network.offline) {
            if (this.validateOrderFree) {
                this.validateOrderFree = false;
                try {
                    await super.validateOrder(...arguments);
                } finally {
                    this.validateOrderFree = true;
                }
            }
        } else {
            await super.validateOrder(...arguments);
        }
    },
    //@override
    async _finalizeValidation() {
        if (this.pos.isCountryGermanyAndFiskaly() && !this.pos.data.network.offline) {
            if (this.currentOrder.isTransactionInactive()) {
                try {
                    this.env.services.ui.block();
                    this.pos.transactionMutex.exec(async () => {
                        return await this.pos.createTransaction(this.currentOrder);
                    });
                } catch (error) {
                    this.pos.fiskalyError(error);
                } finally {
                    this.env.services.ui.unblock();
                }
            }
            if (this.currentOrder.isTransactionStarted() && !this.currentOrder.fiskalyServerError) {
                try {
                    this.env.services.ui.block();
                    await this.pos.transactionMutex.exec(async () => {
                        await this.pos.finishShortTransaction(this.currentOrder);
                    });
                    await super._finalizeValidation(...arguments);
                } catch (error) {
                    this.pos.fiskalyError(error);
                } finally {
                    this.env.services.ui.unblock();
                }
            } else if (
                this.currentOrder.isTransactionFinished() ||
                this.currentOrder.fiskalyServerError
            ) {
                await super._finalizeValidation(...arguments);
            }
        } else {
            await super._finalizeValidation(...arguments);
        }
    },
});
