import { Component, props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One, many2OneProps } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription } from "@web/views/fields/many2one/many2one_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class ForcedPlaceholder extends Many2One {
    static template = "stock.ForcedPlaceholder";
    static components = { ...Many2One.components };
    props = props({ ...many2OneProps });
}

export class ForcedPlaceholderField extends Component {
    static template = "stock.ForcedPlaceholderField";
    static components = { ForcedPlaceholder };
    // Inline conversion of Many2OneField.props (still declared old-style in
    // @web/views/fields/many2one/many2one_field, without an exported schema).
    props = props({
        ...standardFieldProps,
        canCreate: t.boolean().optional(),
        canCreateEdit: t.boolean().optional(),
        canOpen: t.boolean().optional(),
        canQuickCreate: t.boolean().optional(),
        canScanBarcode: t.boolean().optional(),
        canWrite: t.boolean().optional(),
        context: t.object().optional(),
        decorations: t.object().optional(),
        domain: t.or([t.array(), t.function()]).optional(),
        nameCreateField: t.string().optional(),
        openActionContext: t.string().optional(),
        placeholder: t.string().optional(),
        searchLimit: t.number().optional(),
        searchThreshold: t.number().optional(),
        string: t.string().optional(),
    });

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
