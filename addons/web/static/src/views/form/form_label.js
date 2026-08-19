import { Component, t, usePlugin, useProps } from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { fieldVisualFeedback } from "@web/views/fields/field";
import { getTooltipInfo } from "@web/views/fields/field_tooltip";

export const formLabelProps = {
    fieldInfo: t.object(),
    record: t.object(),
    fieldName: t.string(),
    className: t.string().optional(),
    string: t.string(),
    id: t.string(),
    notMuttedLabel: t.boolean().optional(),
};

export class FormLabel extends Component {
    static template = "web.FormLabel";
    props = useProps(formLabelProps);

    debugMode = usePlugin(DebugModePlugin);

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
        return this.debugMode.isActive() || this.tooltipHelp;
    }

    get tooltipHelp() {
        const field = this.props.record.fields[this.props.fieldName];
        let help = this.props.fieldInfo.help || field.help || "";
        if (field.company_dependent && user.allowedCompanies.length > 1) {
            help += (help ? "\n\n" : "") + _t("Values set here are company-specific.");
        }
        return help;
    }
    get tooltipInfo() {
        if (!this.debugMode.isActive()) {
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
