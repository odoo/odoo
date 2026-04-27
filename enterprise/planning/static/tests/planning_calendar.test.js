import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, queryText, waitFor } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import {
    clickEvent,
    resizeEventToTime,
    clickDate,
} from "@web/../tests/views/calendar/calendar_test_helpers";
import {
    definePlanningModels,
    planningModels,
    PlanningRole,
    ResourceResource,
} from "./planning_mock_models";

import {
    defineActions,
    getService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    mountView,
    contains,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

describe.current.tags("desktop");

class PlanningSlot extends planningModels.PlanningSlot {
    _records = [
        {
            id: 1,
            name: "First Record",
            start_datetime: "2019-03-11 08:00:00",
            end_datetime: "2019-03-11 12:00:00",
            resource_id: 1,
            color: 7,
            role_id: 1,
            state: "draft",
            repeat: true,
        },
        {
            id: 2,
            name: "Second Record",
            start_datetime: "2019-03-13 08:00:00",
            end_datetime: "2019-03-13 12:00:00",
            resource_id: 2,
            color: 9,
            role_id: 2,
            state: "published",
        },
    ];
    _views = {
        calendar: `<calendar class="o_planning_calendar_test"
                        event_open_popup="true"
                        date_start="start_datetime"
                        date_stop="end_datetime"
                        color="color"
                        mode="week"
                        js_class="planning_calendar">
                            <field name="resource_id" />
                            <field name="role_id" filters="1" color="color"/>
                            <field name="state"/>
                            <field name="repeat"/>
                            <field name="recurrence_update"/>
                            <field name="end_datetime"/>
                    </calendar>`,
        list: `<list js_class="planning_tree"><field name="resource_id"/></list>`,
        "form,1": `<form>
                    <field name="start_datetime"/>
                    <field name="end_datetime"/>
                </form>`,
    };
}

planningModels.PlanningSlot = PlanningSlot;

definePlanningModels();
defineActions([
    {
        id: 1,
        name: "planning action",
        res_model: "planning.slot",
        views: [
            [false, "calendar"],
            [false, "list"],
        ],
    },
]);

onRpc("has_access", () => true);

beforeEach(() => {
    ResourceResource._records = [
        { id: 1, name: "Chaganlal" },
        { id: 2, name: "Maganlal" },
    ];
    PlanningRole._records = [
        { id: 1, name: "JavaScript Developer", color: 1 },
        { id: 2, name: "Functional Consultant", color: 2 },
    ];

    mockDate("2019-03-13 00:00:00", +1);
});

test("planning calendar view: copy previous week", async () => {
    onRpc("action_copy_previous_week", () => {
        expect.step("copy_previous_week()");
        return {};
    });
    onRpc("auto_plan_ids", function () {
        this.env["planning.slot"].write([2], { resource_id: 1 });
        return { open_shift_assigned: [2] };
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    patchWithCleanup(getService("action"), {
        async doAction(action) {
            expect(action).toBe("planning.planning_send_action", {
                message: "should open 'Send Planning By Email' form view",
            });
        },
    });

    await click(".o_control_panel_main_buttons .o_button_copy_previous_week");
    await animationFrame();
    // verify action_copy_previous_week() invoked
    expect.verifySteps(["copy_previous_week()"]);

    // deselect "Maganlal" from Assigned to
    await click(".o_calendar_filter_item[data-value='2'] > input");
    await animationFrame();
    expect(".fc-event").toHaveCount(1, {
        message: "should display 1 events on the week",
    });
    await click(".o_control_panel_main_buttons .o_button_send_all");
    await animationFrame();

    // Switch the view and verify the notification
    expect(".o_notification_body").toHaveCount(1);
    await click(".o_switch_view.o_list");
    await animationFrame();
    await click(".o_switch_view.o_calendar");
    await animationFrame();
    expect(".o_notification_body").toHaveCount(0);

    // Check for auto plan
    await click(".btn.btn-secondary[title='Automatically plan open shifts and sales orders']");
    await animationFrame();

    // Switch the view and verify the notification
    expect(".o_notification_body").toHaveCount(1);
    await click(".o_switch_view.o_list");
    await animationFrame();
    await click(".o_switch_view.o_calendar");
    await animationFrame();
    expect(".o_notification_body").toHaveCount(0);
});

test("Verify Hours in Planning Dialog When Clicking on Off Days and Working Days Calendar view", async () => {
    onRpc("get_unusual_days", () => ({ "2019-03-03": true, "2019-03-09": true }));
    await mountView({
        resModel: "planning.slot",
        type: "calendar",
        arch: `<calendar class="o_planning_calendar_test"
                    date_start="start_datetime"
                    date_stop="end_datetime"
                    color="color"
                    mode="month"
                    show_unusual_days="1"
                    quick_create="1"
                    quick_create_view_id="1"
                    js_class="planning_calendar"
                />`,
    });

    // click on dayoff day
    await clickDate("2019-03-09");
    await waitFor(".o_dialog .o_form_view");
    expect(`.o_field_widget[name="start_datetime"] input`).toHaveValue("03/09/2019 00:00:00", {
        message: "The start date should be the minimum time for the selected date.",
    });
    expect(`.o_field_widget[name="end_datetime"] input`).toHaveValue("03/09/2019 23:59:59", {
        message: "The end date should be the maximum time for the selected date.",
    });
    await contains(`.modal-dialog .o_form_button_save`).click();

    // click on working day
    await clickDate("2019-03-21");
    await waitFor(".o_dialog .o_form_view");
    expect(`.o_field_widget[name="start_datetime"] input`).toHaveValue("03/21/2019 00:00:00", {
        message: "The start date should be the minimum time for the selected date.",
    });
    expect(`.o_field_widget[name="end_datetime"] input`).toHaveValue("03/21/2019 23:59:59", {
        message: "The end date should be the maximum time for the selected date.",
    });
    await contains(`.modal-dialog .o_form_button_save`).click();
});

test("Resize or Drag-Drop should open recurrence update wizard", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    // Change the time of the repeat and normal pills
    await resizeEventToTime(1, "2019-03-11 14:30:00");
    await resizeEventToTime(2, "2019-03-13 14:30:00");

    // In recurrence update wizard -> Select "This shift" and confirm
    await click(".modal-content .btn-primary");
    await animationFrame();

    // Open popover of the repeat pill
    await clickEvent(1);
    expect(".o_cw_popover").toHaveCount(1, { message: "should open a popover clicking on event" });
    expect(
        queryText(
            ".o_cw_popover .o_cw_popover_fields_secondary .list-group-item .o_field_datetime"
        ).split(" ")[1]
    ).toBe("14:30:00", {
        message: "should have correct start date",
    });

    // Open popover of the normal pill
    await clickEvent(2);
    expect(".o_cw_popover").toHaveCount(1, { message: "should open a popover clicking on event" });
    expect(
        queryText(
            ".o_cw_popover .o_cw_popover_fields_secondary .list-group-item .o_field_datetime"
        ).split(" ")[1]
    ).toBe("14:30:00", {
        message: "should have correct start date",
    });
});

test("should display a popover with an Edit button for users with admin access when open popover", async () => {
    onRpc("has_group", ({ args }) => args[1] === "planning.group_planning_manager");
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    // Open popover of the pill
    await clickEvent(1);
    expect(".o_cw_popover").toHaveCount(1, {
        message: "A popover should open when clicking on the event.",
    });
    expect(".o_cw_popover .o_cw_popover_edit").toHaveCount(1, {
        message: "The popover should contain an Edit button in the footer.",
    });
});

test("should not display an Edit button in the popover for users without admin access when open popover", async () => {
    onRpc("has_group", ({ args }) => args[1] !== "planning.group_planning_manager");
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    // Open popover of the pill
    await clickEvent(1);
    expect(".o_cw_popover").toHaveCount(1, {
        message: "A popover should open when clicking on the event.",
    });
    expect(".o_cw_popover .o_cw_popover_edit").toHaveCount(0, {
        message: "The popover should not contain an Edit button in the footer.",
    });
});
