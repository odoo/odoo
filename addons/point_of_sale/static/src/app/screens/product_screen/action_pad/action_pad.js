/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @props partner
 */
export class ActionpadWidget extends Component {
    static template = "point_of_sale.ActionpadWidget";
    static defaultProps = {
        isActionButtonHighlighted: false,
    };

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
    }

    get isLongName() {
        return this.props.partner && this.props.partner.name.length > 10;
    }
    get highlightPay() {
        return this.pos.get_order()?.orderlines?.length;
    }
    getMainButtonClasses() {
        return "button btn d-flex flex-column flex-fill align-items-center justify-content-center fw-bolder btn-lg py-5 rounded-0";
    }
}
