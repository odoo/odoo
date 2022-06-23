/**@odoo-module */

import { fieldVisualFeedback } from "@web/views/fields/field";
import { session } from "@web/session";
import { getTooltipInfo } from "@web/views/fields/field_tooltip";

const { Component, xml } = owl;

export class FormLabel extends Component {
    get className() {
        const { invalid, empty } = fieldVisualFeedback(
            this.props.fieldInfo.FieldComponent,
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
        return classes.join(" ");
    }

    get hasBigTooltip() {
        return Boolean(odoo.debug) || this.tooltipHelp;
    }

    get tooltipHelp() {
        const field = this.props.record.fields[this.props.fieldName];
        let help = field.help || "";
        if (field.company_dependent && session.display_switch_company_menu) {
            help += (help ? "\n\n" : "") + this.env._t("Values set here are company-specific.");
        }
        return help;
    }
    get tooltipInfo() {
        return getTooltipInfo({
            viewMode: "form",
            resModel: this.props.record.resModel,
            field: this.props.record.fields[this.props.fieldName],
            fieldInfo: this.props.fieldInfo,
            help: this.tooltipHelp,
        });
    }
}
FormLabel.template = xml`
  <label class="o_form_label" t-att-for="props.id" t-att-class="className" t-att="{'data-tooltip-template': hasBigTooltip ? 'web.FieldTooltip' : false, 'data-tooltip-info': hasBigTooltip ? tooltipInfo : false}">
    <t t-esc="props.string" />
  </label>
`;
