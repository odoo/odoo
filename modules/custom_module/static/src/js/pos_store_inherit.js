/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(PosStore.prototype, {

    async setup() {
        await super.setup(...arguments);
    },

    createNewOrder(data = {}) {

        return super.createNewOrder(data);
    },

    getPrintingChanges(order, diningModeUpdate) {
        console.log("order", order);

        if (!order.ticket_number || order.ticket_number === 0) {
            // Obtenir la date actuelle
            const today = new Date();
            const todayString = today.toDateString(); // "Tue May 27 2025"

            // Vérifier la dernière date de reset
            const lastResetDate = localStorage.getItem("pos.last_reset_date");
            const currentCounter = parseInt(localStorage.getItem("pos.ticket_number")) || 0;

            let newTicketNumber;

            if (lastResetDate !== todayString) {
                // Nouveau jour - reset à 1
                newTicketNumber = 1;
                localStorage.setItem("pos.ticket_number", "1");
                localStorage.setItem("pos.last_reset_date", todayString);
                console.log("🔄 Reset quotidien - Nouveau ticket #1");
            } else {
                // Même jour - incrémenter
                newTicketNumber = currentCounter + 1;
                localStorage.setItem("pos.ticket_number", newTicketNumber.toString());
                console.log(`📝 Nouveau ticket #${newTicketNumber} pour aujourd'hui`);
            }

            // Assigner le numéro
            order.ticket_number = newTicketNumber;
            this.ticket_number = newTicketNumber;

        } else {
            this.ticket_number = parseInt(order.ticket_number);
            console.log("♻️ Réutilisation ticket existant:", order.ticket_number);
        }

        const time = DateTime.now().toFormat("dd/MM/yyyy HH:mm");

        return {
            table_name: order.table_id ? order.table_id.table_number : "",
            floor_name: order.table_id?.floor_id.name || "",
            config_name: order.config.name,
            time: time,
            tracking_number: order.tracking_number,
            ticket_number: this.ticket_number,
            takeaway: order.config.takeaway && order.takeaway,
            employee_name: order.employee_id?.name || order.user_id?.name,
            order_note: order.general_note,
            diningModeUpdate: diningModeUpdate,
        };
    },
     getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.is_spanish = this.config.is_spanish;
        result.simplified_partner_id = this.config.simplified_partner_id.id;
        if (order) {
            result.is_l10n_es_simplified_invoice = order.is_l10n_es_simplified_invoice;
            result.partner = order.get_partner();
            result.invoice_name = order.invoice_name;
        }
        return result;
    },
     getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.ticket_number = order.ticket_number;
        return result;
    },

    async showLoginScreen() {
        this.showScreen("FloorScreen");
        this.reset_cashier();
        this.showScreen("LoginScreen");
        this.dialog.closeAll();
    }


});