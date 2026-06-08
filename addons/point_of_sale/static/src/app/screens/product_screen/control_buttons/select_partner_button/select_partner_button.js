import { Component, props } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class SelectPartnerButton extends Component {
    static template = "point_of_sale.SelectPartnerButton";
    props = props(["partner?"]);

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
    }
}
