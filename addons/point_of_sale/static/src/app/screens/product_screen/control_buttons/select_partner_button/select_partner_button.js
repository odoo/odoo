import { Component, props, t } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class SelectPartnerButton extends Component {
    static template = "point_of_sale.SelectPartnerButton";
    props = props({
        partner: t.any().optional(),
    });
    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
    }
}
