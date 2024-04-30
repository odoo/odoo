// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { NumericInput } from "@point_of_sale/app/generic_components/inputs/numeric_input/numeric_input";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class EventRegistrationPopup extends Component {
    static template = "pos_event.EventRegistrationPopup";
    static props = ["data", "getPayload", "close"];
    static components = {
        Dialog,
        ProductCard,
        NumericInput,
    };
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.state = useState([]);
        this.dataInQty = this.props.data.reduce((acc, data) => {
            for (let i = 0; i < data.qty; i++) {
                acc.push(data);
            }
            return acc;
        }, []);

        for (const [idx, data] of Object.entries(this.dataInQty)) {
            this.state[idx] = {
                ticket_id: data.ticket_id,
                product_id: data.product_id,
                name: "d",
                email: "d",
                phone: "d",
            };
        }
    }
    confirm() {
        const required = this.state.some(
            (data) => data.name === "" || data.email === "" || data.phone === ""
        );

        if (required) {
            this.dialog.add(AlertDialog, {
                title: "Error",
                body: "Please fill in all required fields",
            });
            return;
        }

        const registrationsByTickets = this.state.reduce((acc, data) => {
            if (!acc[data.ticket_id.id]) {
                acc[data.ticket_id.id] = [];
            }
            acc[data.ticket_id.id].push({
                name: data.name,
                email: data.email,
                phone: data.phone,
            });
            return acc;
        }, {});

        this.props.getPayload(registrationsByTickets);
        this.props.close();
    }
    close() {
        this.props.close();
    }
}
