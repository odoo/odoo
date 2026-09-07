import { animationFrame, click, expect, test } from "@web/../lib/hoot/hoot";
import { mountView } from "@web/../tests/_framework/view_test_helpers";
import { defineResourceModels } from "../../resource_test_helpers";
import { ResourceCalendar } from "../../mock_server/mock_models/resource_calendar";
import { findComponent, makeServerError, onRpc } from "@web/../tests/web_test_helpers";
import { CalendarTypeConfirmRadioField } from "@resource/views/fields/calendar_type_confirm_radio/calendar_type_confirm_radio_field";

defineResourceModels();

test.tags("desktop");
test(`switch calendar_type of a used calendar`, async () => {
    ResourceCalendar.prototype.is_calendar_referenced = () => true;
    const view = await mountView({
        resId: 1,
        resModel: "resource.calendar",
        type: "form",
    });
    const calendar_type_radio = findComponent(
        view,
        (c) => c instanceof CalendarTypeConfirmRadioField
    );
    await click("input[data-value='fixed']");
    await animationFrame();
    await click(".modal-footer .btn:contains('Discard')");
    await animationFrame();
    expect(calendar_type_radio.props.record.data.calendar_type).toBe("variable");
    await click("input[data-value='fixed']");
    await animationFrame();
    await click(".modal-footer .btn:contains('Continue')");
    expect(calendar_type_radio.props.record.data.calendar_type).toBe("fixed");
});

test.tags("desktop");
test(`switch calendar_type of a used calendar: discard the change if the save fails`, async () => {
    expect.errors(1);
    ResourceCalendar.prototype.is_calendar_referenced = () => true;
    onRpc("web_save", () => {
        throw makeServerError({ type: "ValidationError", message: "You can't change this working schedule" });
    });
    const view = await mountView({
        resId: 1,
        resModel: "resource.calendar",
        type: "form",
    });
    const calendar_type_radio = findComponent(
        view,
        (c) => c instanceof CalendarTypeConfirmRadioField
    );
    await click("input[data-value='fixed']");
    await animationFrame();
    await click(".modal-footer .btn:contains('Continue')");
    await animationFrame();
    expect.verifyErrors(["You can't change this working schedule"]);
    expect(calendar_type_radio.props.record.data.calendar_type).toBe("variable");
    expect(calendar_type_radio.props.record.dirty).toBe(false);
});
