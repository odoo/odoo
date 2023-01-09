/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

/**
 * @props partner
 * @emits click-partner
 * @emits click-pay
 */
class ActionpadWidget extends PosComponent {
    get isLongName() {
        return this.props.partner && this.props.partner.name.length > 10;
    }
}
ActionpadWidget.template = "ActionpadWidget";
ActionpadWidget.defaultProps = {
    isActionButtonHighlighted: false,
};

Registries.Component.add(ActionpadWidget);

export default ActionpadWidget;
