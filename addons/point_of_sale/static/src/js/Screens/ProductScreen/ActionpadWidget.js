/** @odoo-module */

import { LegacyComponent } from "@web/legacy/legacy_component";

/**
 * @props partner
 * @emits click-partner
 * @emits click-pay
 */
export class ActionpadWidget extends LegacyComponent {
    static template = "ActionpadWidget";
    static defaultProps = {
        isActionButtonHighlighted: false,
    };

    get isLongName() {
        return this.props.partner && this.props.partner.name.length > 10;
    }
}
