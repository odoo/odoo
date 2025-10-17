import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import {
    fieldSelectorField,
    FieldSelectorField,
} from "@web/views/fields/field_selector/field_selector_field";

export class MailFieldSelectorField extends fieldSelectorField.component {
    static props = {
        ...FieldSelectorField.props,
        onlyTracking: { type: Boolean, optional: true },
    };
    setup() {
        super.setup();
        this.fieldService = useService("field");
        onWillStart(async () => {
            const fields = await this.fieldService.loadFields(this.resModel, {
                attributes: ["tracking"],
            });
            this.tracking_fields_name = Object.entries(fields)
                .filter(([, finfo]) => finfo.tracking)
                .map(([name]) => name);
        });
    }

    filter(fieldDef) {
        if (this.props.onlyTracking && !this.tracking_fields_name.includes(fieldDef.name)) {
            return false;
        }
        return super.filter(fieldDef);
    }
}

export const mailFieldSelectorField = {
    ...fieldSelectorField,
    component: MailFieldSelectorField,
    supportedOptions: [
        ...fieldSelectorField.supportedOptions,
        {
            label: _t("Only tracking"),
            name: "only_tracking",
            type: "boolean",
            default: false,
        },
    ],
    extractProps({ options }, dynamicInfo) {
        return {
            ...fieldSelectorField.extractProps({ options }, dynamicInfo),
            onlyTracking: options.only_tracking ?? false,
        };
    },
};

registry.category("fields").add("mail_field_selector", mailFieldSelectorField);
