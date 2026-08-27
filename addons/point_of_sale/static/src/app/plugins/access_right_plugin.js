import { Plugin } from "@odoo/owl";

export class PosAccessRightPlugin extends Plugin {
    setup() {
        this.cashier = null;
    }
    init({ pos }) {
        this.pos = pos;
    }
    cashierLogIn() {
        const selectedScreen =
            this.pos.previousScreen && this.pos.previousScreen !== "LoginScreen"
                ? this.pos.previousScreen
                : this.pos.defaultPage;
        const order = this.pos.getOrder();
        if (!order && selectedScreen.page === "ProductScreen") {
            this.pos.addNewOrder();
        }
        const params =
            selectedScreen.page === "ProductScreen" ? { orderUuid: this.pos.getOrder().uuid } : {};
        this.pos.navigate(selectedScreen.page, params);
        this.pos.hasLoggedIn = true;
    }
    /**
     * Return the current cashier (in this case, the user)
     * @returns {name: string, id: int, role: string}
     */
    get loggedCashier() {
        return this.pos.user;
    }
    get cashierUserId() {
        return this.pos.user?.id;
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
        return true;
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
