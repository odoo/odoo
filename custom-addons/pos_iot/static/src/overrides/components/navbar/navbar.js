/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { LastTransactionStatusButton } from "@pos_iot/app/last_transaction_status/last_transaction_status";

patch(Navbar, {
    components: { ...Navbar.components, LastTransactionStatusButton },
});
