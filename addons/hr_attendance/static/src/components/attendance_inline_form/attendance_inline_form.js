import { Component, t, useProps } from "@odoo/owl";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
import { Field } from "@web/views/fields/field";
import { useStatusIndicator } from "@web/views/form/form_status_indicator/form_status_indicator";

export class AttendanceInlineForm extends Component {
    static components = { DateTimeField, Field };
    static template = "hr_attendance.AttendanceInlineForm";

    props = useProps({
        record: t.object(),
        onKeydown: t.function(),
        onSave: t.function(),
        onDiscard: t.function(),
        showBreak: t.boolean(),
    });

    setup() {
        this.statusIndicator = useStatusIndicator(this.props.record.model);
    }

    get isDirty() {
        return this.statusIndicator.props().isDirty;
    }
}
