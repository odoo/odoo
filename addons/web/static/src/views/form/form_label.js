// @ts-check

/** @module @web/views/form/form_label - Label component for form fields with tooltip, validity, and company-dependent indicators */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { fieldVisualFeedback } from "@web/fields/field";
import { getTooltipInfo } from "@web/fields/field_tooltip";
import { user } from "@web/services/user";

/** Label component for form fields, with tooltip, validity, and company-dependent indicators. */
export class FormLabel extends Component {
    static template = "web.FormLabel";
    static props = {
        fieldInfo: { type: Object },
        record: { type: Object },
        fieldName: { type: String },
        className: { type: String, optional: true },
        string: { type: String },
        id: { type: String },
        notMuttedLabel: { type: Boolean, optional: true },
    };

    /** @returns {string} space-separated CSS classes reflecting field validity, emptiness, and readonly state */
    get className() {
        const { invalid, empty, readonly } = fieldVisualFeedback(
            this.props.fieldInfo.field,
            this.props.record,
            this.props.fieldName,
            this.props.fieldInfo,
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

    /** @returns {boolean} whether the label should display a tooltip */
    get hasTooltip() {
        return Boolean(odoo.debug) || this.tooltipHelp;
    }

    /** @returns {string} help text for the tooltip, including company-dependent notice */
    get tooltipHelp() {
        const field = this.props.record.fields[this.props.fieldName];
        let help = this.props.fieldInfo.help || field.help || "";
        if (field.company_dependent && user.allowedCompanies.length > 1) {
            help += (help ? "\n\n" : "") + _t("Values set here are company-specific.");
        }
        return help;
    }
    /** @returns {string} JSON-serialized tooltip info for the field popover */
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
