import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class SelectPartnerButton extends Component {
    static template = "point_of_sale.SelectPartnerButton";
    static props = ["partner?"];
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
    }
}
