import { Plugin, usePlugin, signal } from "@odoo/owl";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { DialogPlugin } from "@web/core/dialog/dialog_plugin";
import { PosRouterPlugin } from "@point_of_sale/app/plugins/pos_router_plugin";

export class PosAccessRightPlugin extends Plugin {
    notification = usePlugin(NotificationPlugin);
    dialog = usePlugin(DialogPlugin);
    router = usePlugin(PosRouterPlugin);
    hasLoggedIn = signal(false);

    setup() {
        this.cashier = null;
    }
    init({ data }) {
        this.data = data;
    }

    setCashier(user) {
        if (!user) {
            return;
        }

        this.cashier = user;
        sessionStorage.setItem(`connected_cashier_${this.config.id}`, user.id);
    }

    resetCashier() {
        this.cashier = false;
        sessionStorage.removeItem(`connected_cashier_${this.config.id}`);
    }

    get config() {
        return this.data.models["pos.config"].get(odoo.pos_config_id);
    }

    get session() {
        return this.data.models["pos.session"].get(odoo.pos_session_id);
    }

    /**
     * Return the current cashier (in this case, the user)
     * @returns {name: string, id: int, role: string}
     */
    get loggedCashier() {
        return this.data.models["res.users"].getFirst();
    }
    get cashierUserId() {
        const user = this.data.models["res.users"].getFirst();
        return user.id;
    }
    // Overridden in `pos_planning` module to enrich employees with planning info (subtitles, sorting, etc.)
    getCashierSelectionList(employees) {
        return employees;
    }
    get canOpenRegister() {
        return true;
    }

    get canCloseSession() {
        return true;
    }

    get canPrintReport() {
        return true;
    }

    get canSelectPrinter() {
        return true;
    }

    get canAccessCustomerDisplay() {
        return true;
    }

    get canInstallApp() {
        return true;
    }

    get canGoToBackend() {
        return true;
    }

    get disablePartner() {
        return true;
    }

    get canEditDetails() {
        return true;
    }

    get disableClickPayment() {
        return true;
    }

    get canAccessDebugMode() {
        return true;
    }

    get canSplitOrder() {
        return true;
    }

    get disableValidateOrder() {
        return true;
    }

    get canAccessButton() {
        return true;
    }

    get canAccessProductFinancials() {
        return true;
    }

    get disableToggleFavorite() {
        return true;
    }

    get canAccessQuotation() {
        return true;
    }

    get canAccessPricelist() {
        return true;
    }

    get canAccessFiscalPosition() {
        return true;
    }

    get canApplyDiscount() {
        return true;
    }

    get canApplyPromoCode() {
        return true;
    }

    get canApplyRewards() {
        return true;
    }

    get canCashMove() {
        return true;
    }

    get allowProductEdition() {
        return true;
    }

    get canSortProducts() {
        return true;
    }

    get disableLinediscount() {
        return true;
    }

    get disablePriceButton() {
        return false;
    }

    get canCancelOrder() {
        return true;
    }

    get canDeleteOrder() {
        return true;
    }

    get canShowPads() {
        return true;
    }

    get canEditBooking() {
        return true;
    }

    get canDeleteBooking() {
        return true;
    }

    get canAccessPaymentMethod() {
        return true;
    }

    get canNegateQuantity() {
        return true;
    }

    get canSnooze() {
        return true;
    }

    get disableToggleOrder() {
        return true;
    }

    get canClickOrderLine() {
        return true;
    }

    get disableBackSpaceButton() {
        return true;
    }

    get canSwitchSign() {
        return true;
    }

    get showEditPlanButton() {
        return true;
    }

    get canAccessTotalDue() {
        return true;
    }

    get canSwitchSelfAvailability() {
        return true;
    }

    get canCreateBooking() {
        return true;
    }
}
