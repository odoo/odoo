/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

export class SetReservedQuantityButton extends Component {
    setup() {
        const user = useService('user');
        onWillStart(async () => {
            this.displayUOM = await user.hasGroup('uom.group_uom');
        });
    }

    get uom() {
        const [id, name] = this.props.record.data.product_uom_id || [];
        return { id, name };
    }

    _setQuantity (ev) {
        ev.stopPropagation();
        this.props.record.update({ [this.props.fieldToSet]: this.props.record.data[this.props.name] });
    }
}
SetReservedQuantityButton.props = {
    ...standardFieldProps,
    fieldToSet: { type: String },
};
SetReservedQuantityButton.template = 'stock_barcode.SetReservedQuantityButtonTemplate';

export const setReservedQuantityButton = {
    component: SetReservedQuantityButton,
    extractProps: ({ attrs }) => {
        if (attrs.field_to_set) {
            return { fieldToSet: attrs.field_to_set };
        }
        return {};
    },
};

registry.category("fields").add("set_reserved_qty_button", setReservedQuantityButton);
