/**@odoo-module */

import { fieldVisualFeedback } from "@web/views/fields/field";
import { session } from "@web/session";
import { getTooltipInfo } from "@web/views/fields/field_tooltip";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

export class FormLabel extends Component {
    get className() {
        const { invalid, empty, readonly } = fieldVisualFeedback(
            this.props.fieldInfo.field,
            this.props.record,
            this.props.fieldName,
            this.props.fieldInfo
        );
        const classes = this.props.className ? [this.props.className] : [];
        if (invalid) {
            classes.push("o_field_invalid");
        }
        if (empty) {
            classes.push("o_form_label_empty");
        }
        if (readonly && !this.props.notMuttedLabel) {
            classes.push("o_form_label_readonly");
        }
        return classes.join(" ");
    }

    get hasTooltip() {
        return Boolean(odoo.debug) || this.tooltipHelp;
    }

    get tooltipHelp() {
        const field = this.props.record.fields[this.props.fieldName];
        let help = field.help || "";
        if (field.company_dependent && session.display_switch_company_menu) {
            help += (help ? "\n\n" : "") + _t("Values set here are company-specific.");
        }
        return help;
    }
    get tooltipInfo() {
        if (!odoo.debug) {
            return JSON.stringify({
                field: {
                    help: this.tooltipHelp,
                },
            });
        }
        return getTooltipInfo({
            viewMode: "form",
            resModel: this.props.record.resModel,
            field: this.props.record.fields[this.props.fieldName],
            fieldInfo: this.props.fieldInfo,
            help: this.tooltipHelp,
        });
    }
}
FormLabel.template = "web.FormLabel";
FormLabel.props = {
    fieldInfo: { type: Object },
    record: { type: Object },
    fieldName: { type: String },
    className: { type: String, optional: true },
    string: { type: String },
    id: { type: String },
    notMuttedLabel: { type: Boolean, optional: true },
};
