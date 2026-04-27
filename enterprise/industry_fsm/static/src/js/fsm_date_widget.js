/** @odoo-module **/

import { DateTimeField, dateTimeField } from '@web/views/fields/datetime/datetime_field';
import { formatDateTime } from '@web/core/l10n/dates';
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";

class FsmDateWidget extends DateTimeField {
    static template = "industry_fsm.FsmDateWidget";

    /**
     * @override
     */
    getFormattedValue() {
        const format = localization.timeFormat.search("HH") === 0 ? "HH:mm" : "hh:mm a";
        const { data } = this.props.record;
        if (!data.planned_date_begin){
            return;
        }
        return formatDateTime(data.planned_date_begin, { format: format });
    }
    get className() {
        const date = new Date();
        const widgetcolor = this.props.record.data.date_deadline < date && this.props.record.data.stage_id[1] !== 'Done' ? 'oe_kanban_text_red' : '';
        return widgetcolor;
    }
}

export const fsmDateWidget = {
    ...dateTimeField,
    component: FsmDateWidget,
}

registry.category("fields").add('fsm_date', fsmDateWidget);
