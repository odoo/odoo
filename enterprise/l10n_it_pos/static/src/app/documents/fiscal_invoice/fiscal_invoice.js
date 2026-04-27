import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Header, Body, Footer } from "@l10n_it_pos/app/documents/fiscal_document";
import { PrintRecMessage } from "@l10n_it_pos/app/fiscal_printer/commands";

export class FiscalInvoice extends Component {
    static template = "l10n_it_pos.FiscalInvoice";

    static components = {
        Header,
        PrintRecMessage,
        Body,
        Footer,
    };

    static props = {
        order: {
            type: Object,
            optional: true, // To keep backward compatibility
        },
    };

    setup() {
        this.pos = usePos();
        this.order = this.props.order || this.pos.get_order();
    }

    get client() {
        return this.order.get_partner_name();
    }
}
