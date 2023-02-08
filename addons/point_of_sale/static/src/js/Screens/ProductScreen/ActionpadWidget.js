/** @odoo-module */

import { usePos } from "@point_of_sale/app/pos_hook";
import { Component } from "@odoo/owl";

/**
 * @props partner
 */
export class ActionpadWidget extends Component {
    static template = "ActionpadWidget";
    static defaultProps = {
        isActionButtonHighlighted: false,
    };

    setup() {
        this.pos = usePos();
    }

    get isLongName() {
        return this.props.partner && this.props.partner.name.length > 10;
    }
}
