/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
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
                    const message = {
                        noInternet: _t("Cannot sync the orders with Fiskaly!"),
                        unknown: _t(
                            "An unknown error has occurred! Please contact Odoo for more information."
                        ),
                    };
                    this.pos.fiskalyError(error, message);
                } else {
                    _super_handlePushOrderError(error);
                }
            };
            this.validateOrderFree = true;
        }
    },
    //@override
    async validateOrder(isForceValidate) {
        if (this.pos.isCountryGermanyAndFiskaly()) {
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
        if (this.pos.isCountryGermanyAndFiskaly()) {
            if (this.currentOrder.isTransactionInactive()) {
                try {
                    await this.currentOrder.createTransaction();
                } catch (error) {
                    if (error.status === 0) {
                        this.pos.showFiskalyNoInternetConfirmPopup(this);
                    } else {
                        const message = {
                            unknown: _t("An unknown error has occurred! Please, contact Odoo."),
                        };
                        this.pos.fiskalyError(error, message);
                    }
                }
            }
            if (this.currentOrder.isTransactionStarted()) {
                try {
                    await this.currentOrder.finishShortTransaction();
                    await super._finalizeValidation(...arguments);
                } catch (error) {
                    if (error.status === 0) {
                        this.pos.showFiskalyNoInternetConfirmPopup(this);
                    } else {
                        const message = {
                            unknown: _t("An unknown error has occurred! Please, contact Odoo."),
                        };
                        this.pos.fiskalyError(error, message);
                    }
                }
            }
        } else {
            await super._finalizeValidation(...arguments);
        }
    },
});
