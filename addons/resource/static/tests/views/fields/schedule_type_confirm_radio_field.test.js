import { animationFrame, click, expect, test } from "@web/../lib/hoot/hoot";
import { mountView } from "@web/../tests/_framework/view_test_helpers";
import { defineResourceModels } from "../../resource_test_helpers";
import { ResourceCalendar } from "../../mock_server/mock_models/resource_calendar";
import { findComponent } from "@web/../tests/web_test_helpers";
import { ScheduleTypeConfirmRadioField } from "../../../src/views/fields/schedule_type_confirm_radio/schedule_type_confirm_radio_field";

defineResourceModels();

test.tags("desktop");
test(`switch schedule_type of a used calendar`, async () => {
    ResourceCalendar.prototype.is_calendar_referenced = () => true;
    const view = await mountView({
        resId: 1,
        resModel: "resource.calendar",
        type: "form",
    });
    const schedule_type_radio = findComponent(
        view,
        (c) => c instanceof ScheduleTypeConfirmRadioField
    );
    await click("input[data-value='fixed']");
    await animationFrame();
    await click(".modal-footer .btn:contains('Discard')");
    await animationFrame();
    expect(schedule_type_radio.props.record.data.schedule_type).toBe("variable");
    await click("input[data-value='fixed']");
    await animationFrame();
    await click(".modal-footer .btn:contains('Continue')");
    expect(schedule_type_radio.props.record.data.schedule_type).toBe("fixed");
});
