import { expect, test, describe } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers"
import { TimeOffCard } from "@hr_holidays/dashboard/time_off_card"
import { defineHrHolidaysModels } from "./hr_holidays_test_helpers";

function getHourProps(floatHour) {
	return {
		name: "Extra Hours",
		data: {
			accrual_bonus: 0,
			allows_negative: false,
			closest_allocation_duration: false,
			closest_allocation_expire: false,
			closest_allocation_remaining: 0,
			employee_company: 1,
			exceeding_duration: 0,
			holds_changes: false,
			icon: "/hr_holidays/static/src/img/icons/Compensatory_Time_Off.svg",
			leaves_approved: 0,
			leaves_requested: 0,
			leaves_taken: 0,
			max_allowed_negative: 0,
			overtime_deductible: true,
			unit_of_measure: "hour",
			total_virtual_excess: 0,
			virtual_excess_data: {},
			max_leaves: floatHour,
			remaining_leaves: floatHour,
			virtual_remaining_leaves: floatHour,
			virtual_leaves_taken: floatHour,
		},
		requires_allocation: false,
		holidayStatusId: 6,
		employeeId: null,
	}
}

defineHrHolidaysModels();

describe('Test if card of "hour" unit is well formatted in TimeOffCard', () => {
	test("Basic hour format", async () => {
		// floatHour can be between 0 and +infinity
		const floatHour = 13 + 56 / 60;
		const props = getHourProps(floatHour)
		await mountWithCleanup(TimeOffCard, { props });
		await animationFrame();
		expect("span.o_timeoff_duration span").toHaveText("13:56");
	});

	test("Hour with need of zero padding", async () => {
		const floatHour = 1 + 5 / 60;
		const props = getHourProps(floatHour)
		await mountWithCleanup(TimeOffCard, { props });
		await animationFrame();
		// no need for zeroes for hour since the hour can be any positive number
		expect("span.o_timeoff_duration span").toHaveText("1:05");
	});

	test("Hour of value 0", async () => {
		const floatHour = 0 + 0 / 60;
		const props = getHourProps(floatHour)
		await mountWithCleanup(TimeOffCard, { props });
		await animationFrame();
		expect("span.o_timeoff_duration span").toHaveText("0:00");
	});
});
