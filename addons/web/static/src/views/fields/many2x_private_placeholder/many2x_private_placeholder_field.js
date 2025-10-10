import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import {
    many2ManyTagsField,
    Many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";

export class Many2XPrivatePlaceholderField extends Component {
    static template = "web.Many2XPrivatePlaceholderField";
    static components = { Many2One, Many2ManyTagsField };
    static props = {
        ...Many2OneField.props,
        ...Many2ManyTagsField.props,
    };

    get componentProps() {
        const placeholder =
            !this.props.readonly && this.env.config.viewType === "list" ? "" : _t("Private");
        if (this.isM2OField) {
            const props = computeM2OProps(this.props);
            props.placeholder = placeholder;
            return props;
        } else {
            return {
                ...this.props,
                placeholder: placeholder,
            };
        }
    }

    get isM2OField() {
        return this.props.record.fields[this.props.name].type === "many2one";
    }

    get hasNoValue() {
        const fieldData = this.props.record.data[this.props.name];
        return this.isM2OField ? !fieldData : !fieldData.records || fieldData.records.length === 0;
    }
}

registry.category("fields").add("many2one_private_placeholder", {
    ...buildM2OFieldDescription(Many2XPrivatePlaceholderField),
});

registry.category("fields").add("many2many_private_placeholder", {
    ...many2ManyTagsField,
    component: Many2XPrivatePlaceholderField,
});
