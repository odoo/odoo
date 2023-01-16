/** @odoo-module */

import { PosComponent } from "@point_of_sale/js/PosComponent";

/**
 * @props partner
 * @emits click-partner
 * @emits click-pay
 */
export class ActionpadWidget extends PosComponent {
    static template = "ActionpadWidget";
    static defaultProps = {
        isActionButtonHighlighted: false,
    };

    get isLongName() {
        return this.props.partner && this.props.partner.name.length > 10;
    }
}
