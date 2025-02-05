import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { KanbanMany2One, useMany2One } from "@web/views/fields/many2one/many2one";
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

    setup() {
        this.m2o = useMany2One(() => this.props);
    }

    get displayName() {
        return this.props.displayAvatarName ? this.m2o.displayName : "";
    }

    get m2oProps() {
        return this.m2o.computeProps();
    }
}

/** @type {import("registries").FieldsRegistryItemShape} */
const fieldDescr = {
    ...buildM2OFieldDescription(KanbanMany2OneAvatarUserField),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            displayAvatarName: staticInfo.options.display_avatar_name || false,
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
