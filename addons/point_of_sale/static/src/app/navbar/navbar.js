/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { useService } from "@web/core/utils/hooks";

import { CashierName } from "@point_of_sale/js/ChromeWidgets/CashierName";
import { CustomerFacingDisplayButton } from "@point_of_sale/js/ChromeWidgets/CustomerFacingDisplayButton";
import { ProxyStatus } from "@point_of_sale/js/ChromeWidgets/ProxyStatus";
import { SaleDetailsButton } from "@point_of_sale/js/ChromeWidgets/SaleDetailsButton";
import { SyncNotification } from "@point_of_sale/js/ChromeWidgets/SyncNotification";
import { CashMovePopup } from "./cash_move_popup/cash_move_popup";
import { TicketScreen } from "@point_of_sale/js/Screens/TicketScreen/TicketScreen";
import { BackButton } from "@point_of_sale/app/navbar/BackButton";
import { Component, useState, useExternalListener } from "@odoo/owl";
import { ClosePosPopup } from "@point_of_sale/js/Popups/ClosePosPopup";

export class Navbar extends Component {
    static template = "point_of_sale.Navbar";
    static components = {
        // FIXME POSREF remove some of these components
        CashierName,
        CustomerFacingDisplayButton,
        ProxyStatus,
        SaleDetailsButton,
        SyncNotification,
        BackButton,
    };
    static props = {
        showCashMoveButton: Boolean,
    };
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.debug = useService("debug");
        this.popup = useService("popup");
        this.notification = useService("pos_notification");
        this.hardwareProxy = useService("hardware_proxy");
        this.state = useState({ isMenuOpened: false });
        useExternalListener(window, "mouseup", this.onOutsideClick);
    }

    onOutsideClick() {
        if (this.state.isMenuOpened) {
            this.state.isMenuOpened = false;
        }
    }

    get customerFacingDisplayButtonIsShown() {
        return this.pos.globalState.config.iface_customer_facing_display;
    }

    onCashMoveButtonClick() {
        this.popup.add(CashMovePopup);
    }

    async onTicketButtonClick() {
        if (this.isTicketScreenShown) {
            this.pos.closeScreen();
        } else {
            if (this._shouldLoadOrders()) {
                const { globalState } = this.pos;
                try {
                    globalState.setLoadingOrderState(true);
                    const message = await globalState._syncAllOrdersFromServer();
                    if (message) {
                        this.notification.add(message, 5000);
                    }
                } finally {
                    globalState.setLoadingOrderState(false);
                    this.pos.showScreen("TicketScreen");
                }
            } else {
                this.pos.showScreen("TicketScreen");
            }
        }
    }

    _shouldLoadOrders() {
        return this.pos.globalState.config.trusted_config_ids.length > 0;
    }

    get isTicketScreenShown() {
        return this.pos.mainScreen.component === TicketScreen;
    }

    get orderCount() {
        return this.pos.globalState.get_order_list().length;
    }

    isBurgerMenuClosed() {
        return !this.state.isMenuOpened;
    }

    closeMenu() {
        this.state.isMenuOpened = false;
    }

    openMenu() {
        this.state.isMenuOpened = true;
    }

    async closeSession() {
        const info = await this.pos.globalState.getClosePosInfo();
        this.popup.add(ClosePosPopup, { info, keepBehind: true });
    }

    showBackButton() {
        return this.pos.showBackButton() && this.ui.isSmall;
    }
}
