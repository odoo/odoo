import { Avatar } from "@mail/views/web/fields/avatar/avatar";

import { Component, onWillStart, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { computeM2OProps, KanbanMany2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    m2oSupportedOptions,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";

export class CardMany2OneAvatarEmployeeField extends Component {
    static template = "hr.CardMany2OneAvatarEmployeeField";
    static components = { Avatar, KanbanMany2One };
    props = useProps({
        ...many2OneFieldProps,
        displayAvatarName: t.boolean().optional(),
        relation: t.string().optional(),
    });

    setup() {
        onWillStart(async () => {
            this.isHrUser = await user.hasGroup("hr.group_hr_user");
        });
    }

    get displayName() {
        return this.props.displayAvatarName && this.value ? this.value.display_name : "";
    }

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            canQuickCreate: false,
            relation: this.relation,
        };
    }

    get relation() {
        return this.props.relation ?? (this.isHrUser ? "hr.employee" : "hr.employee.public");
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get uniqueId() {
        // hr_leave_stats widget uses this field but doesn't provide the write_date
        return this.value?.write_date ? this.value.write_date.toMillis() : undefined;
    }
}

/** @type {import("registries").FieldsRegistryItemShape} */
const fieldDescr = {
    ...buildM2OFieldDescription(CardMany2OneAvatarEmployeeField),
    additionalClasses: ["o_field_many2one_avatar_user"],
    relatedFields: [{ name: "write_date", type: "datetime" }],
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            displayAvatarName: staticInfo.options.display_avatar_name || false,
            readonly: dynamicInfo.readonly,
            relation: staticInfo.options.relation,
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

registry.category("fields").add("activity.many2one_avatar_employee", fieldDescr);
registry.category("fields").add("card.many2one_avatar_employee", fieldDescr);
