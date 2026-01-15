import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, KanbanMany2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    m2oSupportedOptions,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";
import { Avatar } from "../avatar/avatar";

export class KanbanMany2OneAvatarUserField extends Component {
    static template = "mail.KanbanMany2OneAvatarUserField";
    static components = { Avatar, KanbanMany2One };
    static props = {
        ...Many2OneField.props,
        displayAvatarName: { type: Boolean, optional: true },
    };

    get displayName() {
        return this.props.displayAvatarName && this.value ? this.value.display_name : "";
    }

    get m2oProps() {
        return computeM2OProps(this.props);
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
}

/** @type {import("registries").FieldsRegistryItemShape} */
const fieldDescr = {
    ...buildM2OFieldDescription(KanbanMany2OneAvatarUserField),
    additionalClasses: ["o_field_many2one_avatar_kanban", "o_field_many2one_avatar"],
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            displayAvatarName: staticInfo.options.display_avatar_name || false,
            readonly: dynamicInfo.readonly,
        };
    },
    supportedOptions: [
        ...m2oSupportedOptions,
        {
            label: _t("Display avatar name"),
            name: "display_avatar_name",
            type: "boolean",
        },
    ],
};

registry.category("fields").add("activity.many2one_avatar_user", fieldDescr);
registry.category("fields").add("kanban.many2one_avatar_user", fieldDescr);
