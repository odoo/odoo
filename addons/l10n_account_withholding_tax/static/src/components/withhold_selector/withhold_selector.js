import { t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { radioField, RadioField, radioFieldProps } from "@web/views/fields/radio/radio_field";

export class WithholdSelector extends RadioField {
    static template = "web.RadioField";
    props = useProps({
        ...radioFieldProps,
        whitelist_fname: t.string().optional(),
    });

    get items() {
        const { record, name, whitelist_fname } = this.props;
        let items = super.items;
        if (whitelist_fname) {
            const allowed = record.data[whitelist_fname] || [];
            items = items.filter((item) => item[0] === record.data[name] || allowed.includes(item[0]));
        }
        if ("reconciled_bills_count" in record.fields && !(record.data.reconciled_bills_count || record.data.reconciled_invoices_count)) {
            items = items.filter((item) => item[0] !== "withhold");
        }
        return items;
    }
}

export const withholdSelector = {
    ...radioField,
    additionalClasses: ["o_field_radio"],
    component: WithholdSelector,
    supportedOptions: [
        ...radioField.supportedOptions,
        {
            label: _t("Allowed values field"),
            name: "whitelist_fname",
            type: "field",
            availableTypes: ["json"],
        },
    ],
    extractProps({ options }) {
        return {
            ...radioField.extractProps(...arguments),
            whitelist_fname: options.whitelist_fname,
        };
    },
};

registry.category("fields").add("withhold_selector", withholdSelector);
