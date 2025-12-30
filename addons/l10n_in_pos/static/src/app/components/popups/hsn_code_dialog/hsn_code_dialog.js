import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class hsnCodeDialog extends Component {
    static components = { Dialog };
    static template = "l10n_in_pos.hsnCodeDialog";
    static props = {
        close: Function,
    };

    setup() {
        this.pos = usePos();
    }

    async redirect() {
        // Close dialog first
        this.props.close();
        const action_xml_id = await this.pos.data.call(
            "product.product",
            "l10n_in_get_hsn_code_action",
            []
        );
        const url = `/odoo/action-${action_xml_id}`;
        window.open(url, "_blank");
    }
}
