/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";
import { usePos } from "@point_of_sale/app/pos_store";

import { CashierName } from "@point_of_sale/js/ChromeWidgets/CashierName";
import { CashMoveButton } from "@point_of_sale/js/ChromeWidgets/CashMoveButton";
import { CustomerFacingDisplayButton } from "@point_of_sale/js/ChromeWidgets/CustomerFacingDisplayButton";
import { HeaderButton } from "@point_of_sale/js/ChromeWidgets/HeaderButton";
import { ProxyStatus } from "@point_of_sale/js/ChromeWidgets/ProxyStatus";
import { SaleDetailsButton } from "@point_of_sale/js/ChromeWidgets/SaleDetailsButton";
import { SyncNotification } from "@point_of_sale/js/ChromeWidgets/SyncNotification";
import { TicketButton } from "@point_of_sale/js/ChromeWidgets/TicketButton";

export class Navbar extends PosComponent {
    static template = "point_of_sale.Navbar";
    static components = {
        // FIXME POSREF remove some of these components
        CashierName,
        CashMoveButton,
        CustomerFacingDisplayButton,
        HeaderButton,
        ProxyStatus,
        SaleDetailsButton,
        SyncNotification,
        TicketButton,
    };
    static props = {
        showCashMoveButton: Boolean,
    };
    setup() {
        this.pos = usePos();
    }
    get customerFacingDisplayButtonIsShown() {
        return this.env.pos.config.iface_customer_facing_display;
    }
}
