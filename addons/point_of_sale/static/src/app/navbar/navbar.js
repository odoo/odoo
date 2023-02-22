/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";
import { usePos } from "@point_of_sale/app/pos_hook";
import { useService } from "@web/core/utils/hooks";

import { CashierName } from "@point_of_sale/js/ChromeWidgets/CashierName";
import { CustomerFacingDisplayButton } from "@point_of_sale/js/ChromeWidgets/CustomerFacingDisplayButton";
import { HeaderButton } from "@point_of_sale/js/ChromeWidgets/HeaderButton";
import { ProxyStatus } from "@point_of_sale/js/ChromeWidgets/ProxyStatus";
import { SaleDetailsButton } from "@point_of_sale/js/ChromeWidgets/SaleDetailsButton";
import { SyncNotification } from "@point_of_sale/js/ChromeWidgets/SyncNotification";
import { CashMovePopup } from "./cash_move_popup/cash_move_popup";
import { TicketScreen } from "@point_of_sale/js/Screens/TicketScreen/TicketScreen";

export class Navbar extends LegacyComponent {
    static template = "point_of_sale.Navbar";
    static components = {
        // FIXME POSREF remove some of these components
        CashierName,
        CustomerFacingDisplayButton,
        HeaderButton,
        ProxyStatus,
        SaleDetailsButton,
        SyncNotification,
    };
    static props = {
        showCashMoveButton: Boolean,
    };
    setup() {
        this.pos = usePos();
        this.debug = useService("debug");
        this.popup = useService("popup");
    }
    get customerFacingDisplayButtonIsShown() {
        return this.env.pos.config.iface_customer_facing_display;
    }

    onCashMoveButtonClick() {
        this.popup.add(CashMovePopup);
    }

    onTicketButtonClick() {
        if (this.isTicketScreenShown) {
            this.pos.closeScreen();
        } else {
            this.pos.showScreen("TicketScreen");
        }
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

    get configName() {
        if (this.env.pos) {
            return this.env.pos.config.name;
        }
        return "Shop";
    }
}
