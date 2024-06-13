import { expect, test } from "@odoo/hoot";
import { click, queryAllTexts } from "@odoo/hoot-dom";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { FAKE_MODEL } from "./calendar_test_helpers";

import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";
import { runAllTimers } from "@odoo/hoot-mock";

const FAKE_PROPS = {
    model: FAKE_MODEL,
};

async function start(props = {}) {
    await mountWithCleanup(CalendarFilterPanel, {
        props: { ...FAKE_PROPS, ...props },
    });
}

test(`render filter panel`, async () => {
    await start({});
    expect(`.o_calendar_filter`).toHaveCount(2);
    expect(`.o_calendar_filter:eq(0) .o_cw_filter_label`).toHaveText("Attendees");
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item`).toHaveCount(4);
    expect(`.o_calendar_filter:eq(1) .o_cw_filter_label`).toHaveText("Users");
    expect(`.o_calendar_filter:eq(1) .o_calendar_filter_item`).toHaveCount(2);
});

test(`filters are correctly sorted`, async () => {
    await start({});
    expect(queryAllTexts`.o_calendar_filter:eq(0) .o_calendar_filter_item`).toEqual([
        "Mitchell Admin",
        "Brandon Freeman",
        "Marc Demo",
        "Everybody's calendar",
    ]);
    expect(queryAllTexts`.o_calendar_filter:eq(1) .o_calendar_filter_item`).toEqual([
        "Brandon Freeman",
        "Marc Demo",
    ]);
});

test(`section can collapse`, async () => {
    await start({});
    expect(`.o_calendar_filter:eq(0) .o_cw_filter_collapse_icon`).toHaveCount(1);
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item`).toHaveCount(4);

    await contains(`.o_calendar_filter:eq(0) .o_cw_filter_label`).click();
    await runAllTimers();
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item`).toHaveCount(0);

    await contains(`.o_calendar_filter:eq(0) .o_cw_filter_label`).click();
    await runAllTimers();
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item`).toHaveCount(4);
});

test(`section cannot collapse`, async () => {
    await start({});
    expect(`.o_calendar_filter:eq(1) .o_cw_filter_label > i`).toHaveCount(0);
    expect(`.o_calendar_filter:eq(1)`).not.toHaveClass("o_calendar_filter-collapsed");
    expect(`.o_calendar_filter:eq(1) .o_calendar_filter_item`).toHaveCount(2);

    await contains(`.o_calendar_filter:eq(1) .o_cw_filter_label`).click();
    await runAllTimers();
    expect(`.o_calendar_filter:eq(1)`).not.toHaveClass("o_calendar_filter-collapsed");
    expect(`.o_calendar_filter:eq(1) .o_calendar_filter_item`).toHaveCount(2);
});

test(`filters can have avatar`, async () => {
    await start({});
    expect(`.o_calendar_filter:eq(0) .o_cw_filter_avatar`).toHaveCount(4);
    expect(`.o_calendar_filter:eq(0) img.o_cw_filter_avatar`).toHaveCount(3);
    expect(`.o_calendar_filter:eq(0) i.o_cw_filter_avatar`).toHaveCount(1);
    expect(
        `.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(0) .o_cw_filter_avatar`
    ).toHaveAttribute("data-src", "/web/image/res.partner/3/avatar_128");
    expect(
        `.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(1) .o_cw_filter_avatar`
    ).toHaveAttribute("data-src", "/web/image/res.partner/4/avatar_128");
    expect(
        `.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(2) .o_cw_filter_avatar`
    ).toHaveAttribute("data-src", "/web/image/res.partner/6/avatar_128");
});

test(`filters cannot have avatar`, async () => {
    await start({});
    expect(`.o_calendar_filter:eq(1) .o_calendar_filter_item`).toHaveCount(2);
    expect(`.o_calendar_filter:eq(1) .o_cw_filter_avatar`).toHaveCount(0);
});

test(`filter can have remove button`, async () => {
    await start({});
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item`).toHaveCount(4);
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item .o_remove`).toHaveCount(2);
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(0) .o_remove`).toHaveCount(0);
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(1) .o_remove`).toHaveCount(1);
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(2) .o_remove`).toHaveCount(1);
    expect(`.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(3) .o_remove`).toHaveCount(0);
});

test(`click on remove button`, async () => {
    await start({
        model: {
            ...FAKE_MODEL,
            unlinkFilter(fieldName, recordId) {
                expect.step(`${fieldName} ${recordId}`);
            },
        },
    });
    click(`.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(1) .o_remove`);
    click(`.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(2) .o_remove`);
    expect(["partner_ids 1", "partner_ids 2"]).toVerifySteps();
});

test(`click on filter`, async () => {
    await start({
        model: {
            ...FAKE_MODEL,
            updateFilters(fieldName, args) {
                expect.step(`${fieldName} ${Object.keys(args)[0]} ${Object.values(args)[0]}`);
            },
        },
    });
    click(`.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(0) input`);
    click(`.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(1) input`);
    click(`.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(2) input`);
    click(`.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(3) input`);
    click(`.o_calendar_filter:eq(0) .o_calendar_filter_item:eq(3) input`);
    expect([
        "partner_ids 3 false",
        "partner_ids 4 false",
        "partner_ids 6 true",
        "partner_ids all true",
        "partner_ids all false",
    ]).toVerifySteps();
});
