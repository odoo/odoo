import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class hsnCodeDialog extends Component {
    static components = { Dialog };
    static template = "l10n_in_pos.hsnCodeDialog";
    static props = {
        close: Function,
        productIds: {
            type: Array,
            optional: false,
        },
    };

    setup() {
        this.pos = usePos();
        this.action = useService("action");
        this.dialog = useService("dialog");
    }

    async redirect() {
        // Close dialog first
        this.props.close();
        const action_xml_id = await this.pos.data.call("product.template", "l10n_in_get_hsn_code_action", [
            this.props.productIds,
        ]);
        const url = "/odoo/action-" + action_xml_id;
        // We could define another action here which shows by default the products available in pos without hsn if it is available (and otherwise they have to update)
        window.open(url, "_blank");
    }
}
