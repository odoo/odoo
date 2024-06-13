import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";
import { patch } from "@web/core/utils/patch";
import { onWillUpdateProps } from "@odoo/owl";

patch(AttendeeCalendarCommonRenderer.prototype, {
	setup() {
		super.setup(...arguments);
		onWillUpdateProps(() => {
			this.fc.api.setOption("businessHours", this.props.model.workingHours)
		});
	},
	get options() {
		return Object.assign(super.options, {
			businessHours: this.props.model.workingHours,
		});
	},
});
