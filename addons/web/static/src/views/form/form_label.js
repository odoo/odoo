/**@odoo-module */

import { fieldVisualFeedback } from "@web/views/fields/field";
import { session } from "@web/session";
import { getTooltipInfo } from "@web/views/fields/field_tooltip";

const { Component, xml } = owl;

export class FormLabel extends Component {
    get className() {
        const { invalid, empty, readonly } = fieldVisualFeedback(
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
        if (readonly) {
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
            help += (help ? "\n\n" : "") + this.env._t("Values set here are company-specific.");
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
FormLabel.template = xml`
  <label class="o_form_label" t-att-for="props.id" t-att-class="className" >
    <t t-esc="props.string"/><sup class="btn-link p-1" t-if="hasTooltip" t-att="{'data-tooltip-template': 'web.FieldTooltip', 'data-tooltip-info': tooltipInfo, 'data-tooltip-touch-tap-to-show': 'true'}">?</sup>
  </label>
`;
