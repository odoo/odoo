import { Component, useProps } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class AttachmentSelector extends Component {
    static template = "sale_expense.AttachmentSelector";
    static components = { CheckBox };
    props = useProps({
        ...standardFieldProps,
    });

    setup() {
        this.selectedAttachments = this.items;
    }

    get items() {
        return this.props.record.data[this.props.name] || [];
    }

    isSelected(id) {
        return this.selectedAttachments.includes((item) => item.id == id && !!item.selected);
    }

    onChange(resId, checked) {
        this.selectedAttachments.find(a => a.id == resId).selected = checked;
        this.props.record.update({ [this.props.name]: this.selectedAttachments });
    }
}

export const attachmentSelector = {
    component: AttachmentSelector,
    displayName: _t("Attachment Selection"),
    supportedTypes: ["json"],
};

registry.category("fields").add("attachment_selector", attachmentSelector);
