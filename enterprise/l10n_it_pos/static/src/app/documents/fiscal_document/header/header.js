import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { PrintRecMessage } from "@l10n_it_pos/app/fiscal_printer/commands";

export class Header extends Component {
    static template = "l10n_it_pos.FiscalDocumentHeader";

    static components = {
        PrintRecMessage,
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
}
