import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class ForcedPlaceholder extends Many2One {
    static template = "stock.ForcedPlaceholder";
    static components = { ...Many2One.components };
    static props = { ...Many2One.props };
}

export class ForcedPlaceholderField extends Component {
    static template = "stock.ForcedPlaceholderField";
    static components = { ForcedPlaceholder };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        const props = computeM2OProps(this.props);
        return {
            ...props,
            canOpen: !props.readonly && props.canOpen, // to remove the wrong link and the hand cursor on hover
        }
    }
}

registry.category("fields").add("stock.forced_placeholder", {
    ...buildM2OFieldDescription(ForcedPlaceholderField),
});
