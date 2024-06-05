import { expect, test, describe } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock"

import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { createElement } from "@web/core/utils/xml";
import { Field } from "@web/views/fields/field";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";

import { defineMailModels } from "@mail/../tests/mail_test_helpers";

defineMailModels();
describe.current.tags("desktop");

const FAKE_DATE = luxon.DateTime.local(2024, 6, 12, 9, 0, 0, 0);

const FAKE_FIELDS = {
    id: { string: "Id", type: "integer" },
    name: { string: "Name", type: "char"},
    stage_id: { string: "Stage", type: "many2one", relation: "project.task.type"},
    state: {
        string: "State",
        type: "selection",
        selection: [
            ["01_in_progress", "In Progress"],
            ["02_changes_requested", "Changes Requested"],
            ["03_approved", "Approved"],
            ["1_done", "Done"],
            ["1_canceled", "Cancelled"],
            ["04_waiting_normal", "Waiting"]
        ],
    },
    start_date: { string: "Start Date", type: "date" },
    stop_date: { string: "Stop Date", type: "date" },
}

const FAKE_RECORDS = {
    1: {
        id: 1,
        name: "Test Popover",
        start_date: luxon.DateTime.local(2024, 6, 7, 11, 30, 0, 0),
        stop_date: luxon.DateTime.local(2024, 6, 11, 15, 30, 0, 0),
        state: "01_in_progress",
        stage_id: [1, "New"],
    }
}

const fakeModelsNode = { 'project.task': { fields: FAKE_FIELDS } };

const FAKE_MODEL = {
    canCreate: true,
    canDelete: true,
    canEdit: true,
    date: FAKE_DATE,
    fieldNames: ["start_date", "stop_date"],
    fields: FAKE_FIELDS,
    firstDayOfWeek: 0,
    popoverFieldNodes: {
        name: Field.parseFieldNode(createElement("field", { name: "name" }), fakeModelsNode, "project.task", "calendar"),
        stage_id: Field.parseFieldNode(createElement("field", { name: "stage_id", widget: "task_stage_with_state_selection" }), fakeModelsNode, "project.task", "calendar"),
    },
    activeFields: {
        name: {},
        stage_id: {},
        state: {readonly: "1", required: "True"},
    },
    rangeEnd: FAKE_DATE.endOf("month"),
    rangeStart: FAKE_DATE.startOf("month"),
    records: FAKE_RECORDS,
    resModel: "event",
    scale: "month",
    scales: ["day", "week", "month", "year"],
    unusualDays: [],
};

const FAKE_PROPS = {
    model: FAKE_MODEL,
    record: {
        id: 1,
        title: "Test Popover",
        isAllDay: true,
        start: luxon.DateTime.local(2024, 6, 7, 11, 30, 0, 0),
        end: luxon.DateTime.local(2024, 6, 11, 15, 30, 0, 0),
        isTimeHidden: true,
        rawRecord: FAKE_RECORDS[1],
    },
    createRecord() {},
    deleteRecord() {},
    editRecord() {},
    close() {},
};

test('check calendar view pop over stage_id and state have been merged', async() => {

    await mountWithCleanup(CalendarCommonPopover, {
        props: { ...FAKE_PROPS },
    });

    await animationFrame();

    //General Fields in Calendar Popover
    expect(queryOne('.list-group-item.align-items-start div[name="name"]').childElementCount).toBe(1);
    // Here the stage and state have been merged as Stage(Label) State(Widget i.e., Value) Stage(Value)
    // Here the count is two because State Widget(Value), Stage Value
    expect(queryOne('.list-group-item.align-items-start div.d-flex').childElementCount).toBe(2);
})
