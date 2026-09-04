/* global Sha1 */

import { PosAccessRightPlugin } from "@point_of_sale/app/plugins/access_right_plugin";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(PosAccessRightPlugin.prototype, {
    async checkPin(employee, pin = false) {
        let inputPin = pin;
        if (!pin) {
            inputPin = await makeAwaitable(this.dialog, NumberPopup, {
                formatDisplayedValue: (x) => x.replace(/./g, "•"),
                title: _t("Password?"),
            });
        } else {
            if (employee._pin !== Sha1.hash(inputPin)) {
                inputPin = await makeAwaitable(this.dialog, NumberPopup, {
                    formatDisplayedValue: (x) => x.replace(/./g, "•"),
                    title: _t("Password?"),
                });
            }
        }
        if (!inputPin || employee._pin !== Sha1.hash(inputPin)) {
            this.notification.add(_t("PIN not found"), {
                type: "warning",
                title: _t(`Wrong PIN`),
            });
            return false;
        }
        return true;
    },
    get loggedCashier() {
        if (this.config.module_pos_hr) {
            return this.cashier;
        }
        return super.loggedCashier;
    },
    get cashierUserId() {
        if (this.config.module_pos_hr) {
            return this.cashier.user_id ? this.cashier.user_id : null;
        }
        return super.cashierUserId;
    },
    _getConnectedCashier() {
        if (!this.config.module_pos_hr) {
            return super._getConnectedCashier(...arguments);
        }
        const cashier_id = Number(sessionStorage.getItem(`connected_cashier_${this.config.id}`));
        if (cashier_id && this.data.models["hr.employee"].get(cashier_id)) {
            return this.data.models["hr.employee"].get(cashier_id);
        }
        return false;
    },
    hasEmployeeRole(roles = []) {
        if (!this.config.module_pos_hr) {
            return true;
        }
        return roles.includes(this.cashier?._role);
    },
    get canOpenRegister() {
        return this.hasEmployeeRole(["cashier", "manager"]);
    },
    get canCloseSession() {
        return this.hasEmployeeRole(["manager"]);
    },
    get canPrintReport() {
        return this.hasEmployeeRole(["manager"]);
    },
    get canSelectPrinter() {
        return this.hasEmployeeRole(["cashier", "manager", "restrictive"]);
    },
    get canAccessCustomerDisplay() {
        return this.hasEmployeeRole(["cashier", "manager", "restrictive"]);
    },
    get canInstallApp() {
        return this.hasEmployeeRole(["cashier", "manager"]);
    },
    get canGoToBackend() {
        return this.hasEmployeeRole(["manager"]);
    },
    get disablePartner() {
        return this.hasEmployeeRole(["cashier", "manager", "restrictive"]);
    },
    get canEditDetails() {
        return this.hasEmployeeRole(["cashier", "manager"]);
    },
    get disableClickPayment() {
        return this.hasEmployeeRole(["cashier", "manager", "restrictive"]);
    },
    get canSplitOrder() {
        return this.hasEmployeeRole(["cashier", "manager"]);
    },
    get disableValidateOrder() {
        return this.hasEmployeeRole(["cashier", "manager", "restrictive"]);
    },
    get canAccessButton() {
        return this.hasEmployeeRole(["cashier", "manager", "restrictive"]);
    },
    get canAccessProductFinancials() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get disableToggleFavorite() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canAccessQuotation() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canAccessPricelist() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canAccessFiscalPosition() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canApplyDiscount() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canApplyPromoCode() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canApplyRewards() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canCashMove() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get allowProductEdition() {
        return this.hasEmployeeRole(["manager"]);
    },
    get canSortProducts() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get disableLinediscount() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get disablePriceButton() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canCancelOrder() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canDeleteOrder() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canShowPads() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canCreateBooking() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canEditBooking() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canDeleteBooking() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canAccessPaymentMethod() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canNegateQuantity() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canSnooze() {
        return this.hasEmployeeRole(["manager", "cashier", "restrictive"]);
    },
    get disableToggleOrder() {
        return this.hasEmployeeRole(["manager", "cashier", "restrictive"]);
    },
    get canClickOrderLine() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get disableBackSpaceButton() {
        return this.hasEmployeeRole(["manager", "cashier", "restrictive"]);
    },
    get canSwitchSign() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get showEditPlanButton() {
        return this.hasEmployeeRole(["manager"]);
    },
    get canAccessDebugMode() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
    get canAccessTotalDue() {
        return this.hasEmployeeRole(["manager", "cashier", "restrictive"]);
    },
    get canSwitchSelfAvailability() {
        return this.hasEmployeeRole(["manager", "cashier"]);
    },
});
