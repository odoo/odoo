import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { DEFAULT_DATE, FAKE_FIELDS, FAKE_MODEL } from "./calendar_test_helpers";

import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";

describe.current.tags("desktop");

const FAKE_RECORD = {
    id: 5,
    title: "Meeting",
    isAllDay: false,
    start: DEFAULT_DATE,
    end: DEFAULT_DATE.plus({ hours: 3, minutes: 15 }),
    colorIndex: 0,
    isTimeHidden: false,
};

const BASE_MODEL = {
    ...FAKE_MODEL,
    records: {
        ...FAKE_MODEL.records,
        5: FAKE_RECORD,
    },
    meta: {
        popover: { fields: [], templates: {} },
        fields: FAKE_FIELDS,
        resModel: "event",
    },
};

const FAKE_PROPS = {
    model: BASE_MODEL,
    resId: 5,
    close() {},
    openRecord() {},
    deleteRecord() {},
};

async function start({ record: recordOverride, ...props } = {}) {
    const baseModel = props.model ?? BASE_MODEL;
    const finalModel = recordOverride
        ? { ...baseModel, records: { ...baseModel.records, 5: recordOverride } }
        : baseModel;
    onRpc("read", ({ args }) => args[0].map((id) => ({ id, display_name: "Meeting" })));
    await mountWithCleanup(CalendarCommonPopover, {
        props: { ...FAKE_PROPS, ...props, model: finalModel },
    });
    await animationFrame();
}

test(`mount a CalendarCommonPopover`, async () => {
    await start();
    expect(`.card-header .popover-header`).toHaveCount(1);
    expect(`.card-header .popover-header`).toHaveText("Meeting");
    expect(`.list-group`).toHaveCount(1);
    expect(`.card-footer .o_cw_popover_edit`).toHaveCount(1);
    expect(`.card-footer .o_cw_popover_delete`).toHaveCount(1);
});

test(`date duration: is all day and is same day`, async () => {
    await start({
        record: { ...FAKE_RECORD, isAllDay: true, isTimeHidden: true },
    });
    expect(`.list-group:eq(0)`).toHaveText("July 16, 2021 All day");
});

test(`date duration: is all day and two days duration`, async () => {
    await start({
        record: {
            ...FAKE_RECORD,
            end: DEFAULT_DATE.plus({ days: 1 }),
            isAllDay: true,
            isTimeHidden: true,
        },
    });
    expect(`.list-group:eq(0)`).toHaveText("July 16-17, 2021 2 days");
});

test(`time duration: 1 hour diff`, async () => {
    await start({
        record: { ...FAKE_RECORD, end: DEFAULT_DATE.plus({ hours: 1 }) },
        model: { ...BASE_MODEL, isDateHidden: true },
    });
    expect(`.list-group:eq(0)`).toHaveText("08:00 - 09:00 (1 hour)");
});

test(`time duration: 2 hours diff`, async () => {
    await start({
        record: { ...FAKE_RECORD, end: DEFAULT_DATE.plus({ hours: 2 }) },
        model: { ...BASE_MODEL, isDateHidden: true },
    });
    expect(`.list-group:eq(0)`).toHaveText("08:00 - 10:00 (2 hours)");
});

test(`time duration: 1 minute diff`, async () => {
    await start({
        record: { ...FAKE_RECORD, end: DEFAULT_DATE.plus({ minutes: 1 }) },
        model: { ...BASE_MODEL, isDateHidden: true },
    });
    expect(`.list-group:eq(0)`).toHaveText("08:00 - 08:01 (1 minute)");
});

test(`time duration: 2 minutes diff`, async () => {
    await start({
        record: { ...FAKE_RECORD, end: DEFAULT_DATE.plus({ minutes: 2 }) },
        model: { ...BASE_MODEL, isDateHidden: true },
    });
    expect(`.list-group:eq(0)`).toHaveText("08:00 - 08:02 (2 minutes)");
});

test(`time duration: 3 hours and 15 minutes diff`, async () => {
    await start({
        model: { ...BASE_MODEL, isDateHidden: true },
    });
    expect(`.list-group:eq(0)`).toHaveText("08:00 - 11:15 (3 hours, 15 minutes)");
});

test(`isDateHidden is true`, async () => {
    await start({
        model: { ...BASE_MODEL, isDateHidden: true },
    });
    expect(`.list-group:eq(0)`).toHaveText("08:00 - 11:15 (3 hours, 15 minutes)");
});

test(`isDateHidden is false`, async () => {
    await start({
        model: { ...BASE_MODEL, isDateHidden: false },
    });
    expect(`.list-group:eq(0)`).toHaveText("July 16, 2021\n08:00 - 11:15 (3 hours, 15 minutes)");
});

test(`isTimeHidden is true`, async () => {
    await start({
        record: { ...FAKE_RECORD, isTimeHidden: true },
    });
    expect(`.list-group:eq(0)`).toHaveText("July 16, 2021");
});

test(`isTimeHidden is false`, async () => {
    await start({
        record: { ...FAKE_RECORD, isTimeHidden: false },
    });
    expect(`.list-group:eq(0)`).toHaveText("July 16, 2021\n08:00 - 11:15 (3 hours, 15 minutes)");
});

test(`canDelete is true`, async () => {
    await start({
        model: { ...BASE_MODEL, canDelete: true },
    });
    expect(`.o_cw_popover_delete`).toHaveCount(1);
});

test(`canDelete is false`, async () => {
    await start({
        model: { ...BASE_MODEL, canDelete: false },
    });
    expect(`.o_cw_popover_delete`).toHaveCount(0);
});

test(`click on delete button`, async () => {
    await start({
        model: { ...BASE_MODEL, canDelete: true },
        deleteRecord: () => expect.step("delete"),
    });
    await click(`.o_cw_popover_delete`);
    expect.verifySteps(["delete"]);
});

test(`click on edit button`, async () => {
    await start({
        openRecord: () => expect.step("edit"),
    });
    await click(`.o_cw_popover_edit`);
    expect.verifySteps(["edit"]);
});
