/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { useService } from "@web/core/utils/hooks";

import { CashierName } from "@point_of_sale/js/ChromeWidgets/CashierName";
import { CustomerFacingDisplayButton } from "@point_of_sale/js/ChromeWidgets/CustomerFacingDisplayButton";
import { HeaderButton } from "@point_of_sale/js/ChromeWidgets/HeaderButton";
import { ProxyStatus } from "@point_of_sale/js/ChromeWidgets/ProxyStatus";
import { SaleDetailsButton } from "@point_of_sale/js/ChromeWidgets/SaleDetailsButton";
import { SyncNotification } from "@point_of_sale/js/ChromeWidgets/SyncNotification";
import { BackendButton } from "@point_of_sale/js/ChromeWidgets/BackendButton";
import { CashMovePopup } from "./cash_move_popup/cash_move_popup";
import { TicketScreen } from "@point_of_sale/js/Screens/TicketScreen/TicketScreen";
import { Component, useState, useExternalListener } from "@odoo/owl";

export class Navbar extends Component {
    static template = "point_of_sale.Navbar";
    static components = {
        // FIXME POSREF remove some of these components
        CashierName,
        CustomerFacingDisplayButton,
        HeaderButton,
        ProxyStatus,
        SaleDetailsButton,
        SyncNotification,
        BackendButton,
    };
    static props = {
        showCashMoveButton: Boolean,
    };
    setup() {
        this.pos = usePos();
        this.debug = useService("debug");
        this.popup = useService("popup");
        this.notification = useService("pos_notification");
        this.hardwareProxy = useService("hardware_proxy");
        this.state = useState({ isMenuOpened: false });
        useExternalListener(window, "mouseup", this.onOutsideClick);
        this.orm = useService("orm");
    }

    onOutsideClick() {
        if (this.state.isMenuOpened) {
            this.state.isMenuOpened = false;
        }
    }

    get customerFacingDisplayButtonIsShown() {
        return this.env.pos.config.iface_customer_facing_display;
    }

    onCashMoveButtonClick() {
        if (this.env.pos.config.iface_cashdrawer) {
            this.onCashMoveButtonClickLog();
        }
        this.popup.add(CashMovePopup);
    }
    async onCashMoveButtonClickLog() {
        this.hardwareProxy.printer.openCashbox();
        await this.orm.call("pos.session", "cash_drawer_open_log", [
            this.pos.globalState.pos_session.id,
            this.env.pos.cashier ? this.env.pos.cashier.id : this.env.pos.user.id,
            "Cash in / out",
        ]);
    }
    async onTicketButtonClick() {
        if (this.isTicketScreenShown) {
            this.pos.closeScreen();
        } else {
            if (this._shouldLoadOrders()) {
                try {
                    this.env.pos.setLoadingOrderState(true);
                    const message = await this.env.pos._syncAllOrdersFromServer();
                    if (message) {
                        this.notification.add(message, 5000);
                    }
                } finally {
                    this.env.pos.setLoadingOrderState(false);
                    this.pos.showScreen("TicketScreen");
                }
            } else {
                this.pos.showScreen("TicketScreen");
            }
        }
    }

    _shouldLoadOrders() {
        return this.env.pos.config.trusted_config_ids.length > 0;
    }

    get isTicketScreenShown() {
        return this.pos.mainScreen.component === TicketScreen;
    }

    get orderCount() {
        // FIXME POSREF: can this condition ever be false?
        if (this.env.pos) {
            return this.env.pos.get_order_list().length;
        }
        return 0;
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
}
