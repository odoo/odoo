import { Component } from "@odoo/owl";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
import { Field } from "@web/views/fields/field";
import { useStatusIndicator } from "@web/views/form/form_status_indicator/form_status_indicator";

export class AttendanceInlineForm extends Component {
    static components = { DateTimeField, Field };
    static props = {
        record: Object,
        onKeydown: Function,
        onSave: Function,
        onDiscard: Function,
        showBreak: Boolean,
    };
    static template = "hr_attendance.AttendanceInlineForm";

    setup() {
        this.statusIndicator = useStatusIndicator(this.props.record.model);
    }

    get isDirty() {
        return this.statusIndicator.props().isDirty;
    }
}
