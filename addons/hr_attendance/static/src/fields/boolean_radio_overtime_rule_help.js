import { registry } from "@web/core/registry";
import { BooleanRadio, booleanRadio } from "../../../../hr/static/src/fields/boolean_radio";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";


class BooleanRadioOvertimeRuleHelp extends BooleanRadio {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.tooltip = null;
        onMounted(() => {
            this._insertHelpText();
        });
    }

    async _insertHelpText() {
        const extra = await this.orm.call(
            "hr.attendance.overtime.rule",
            "get_overtime_rule_form_context",
        );
        this.tooltip = extra && extra.overtime_tooltip;

        if (!this.tooltip) return;

        const fieldName = this.props.name;
        const tooltipEl = document.querySelector(`label[for^="${fieldName}_"] sup[data-tooltip-info]`);
        if (tooltipEl && this.tooltip) {
            const info = JSON.parse(tooltipEl.dataset.tooltipInfo)
            if (info.field) {
                info.field.help = this.tooltip;
            }
            tooltipEl.dataset.tooltipInfo = JSON.stringify(info)
        }
    }
}

registry.category('fields').add('boolean_radio_overtime_help', {
    ...booleanRadio,
    component: BooleanRadioOvertimeRuleHelp,
});
