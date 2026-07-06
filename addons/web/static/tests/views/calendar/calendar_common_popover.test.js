import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { defineModels, fields, models, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { DEFAULT_DATE, FAKE_FIELDS, FAKE_MODEL } from "./calendar_test_helpers";

import { parseXML } from "@web/core/utils/xml";
import { CalendarArchParser } from "@web/views/calendar/calendar_arch_parser";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";

class Partner extends models.Model {
    _name = "res.partner";

    name = fields.Char();

    _records = [{ id: 1, name: "Some partner" }];
}

class Event extends models.Model {
    _name = "event";

    name = fields.Char();
    display_name = fields.Char();
    description = fields.Html();
    partner_id = fields.Many2one({ relation: "res.partner" });

    _records = [
        {
            id: 5,
            name: "Meeting",
            display_name: "Meeting",
            description: "<p>Test description</p>",
            partner_id: 1,
        },
    ];

    _views = {
        "card,1": /* xml */ `
            <card>
                <templates>
                    <t t-name="card">
                        <div class="o_custom_card_body">
                            <field name="display_name"/>
                        </div>
                    </t>
                </templates>
            </card>
        `,
    };
}

defineModels([Event, Partner]);

const FAKE_RECORD = {
    id: 5,
    title: "Meeting",
    isAllDay: false,
    start: DEFAULT_DATE,
    end: DEFAULT_DATE.plus({ hours: 3, minutes: 15 }),
    colorIndex: 0,
    isTimeHidden: false,
    rawRecord: {
        name: "Meeting",
        description: "<p>Test description</p>",
    },
};

const FAKE_PROPS = {
    model: FAKE_MODEL,
    record: FAKE_RECORD,
    openRecord() {},
    deleteRecord() {},
    close() {},
};

async function start({ arch, model = FAKE_MODEL, ...props } = {}) {
    if (arch) {
        const { popover } = new CalendarArchParser().parse(
            parseXML(arch),
            { fake: { fields: FAKE_FIELDS } },
            "fake"
        );
        model = { ...model, meta: { ...model.meta, popover } };
    }
    await mountWithCleanup(CalendarCommonPopover, {
        props: { ...FAKE_PROPS, ...props, model },
    });
}

test(`mount a CalendarCommonPopover`, async () => {
    await start();
    expect(`.o_popover_header`).toHaveCount(1);
    expect(`.o_popover_header`).toHaveText("Meeting");
    expect(`.o_card_record`).toHaveCount(1);
    expect(`.o_card_record div[name="description"]`).toHaveCount(1);
    expect(`.o_popover_footer .o_cw_popover_edit`).toHaveCount(1);
    expect(`.o_popover_footer .o_cw_popover_delete`).toHaveCount(1);
});

test(`date duration: is all day and is same day`, async () => {
    await start({
        record: { ...FAKE_RECORD, isAllDay: true, isTimeHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("July 16, 2021");
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
    expect(`.o_card_record > div:eq(0)`).toHaveText("July 16-17, 2021\n2 days");
});

test(`time duration: 1 hour diff`, async () => {
    await start({
        record: { ...FAKE_RECORD, end: DEFAULT_DATE.plus({ hours: 1 }) },
        model: { ...FAKE_MODEL, isDateHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("08:00 - 09:00\n(1 hour)");
});

test(`time duration: 2 hours diff`, async () => {
    await start({
        record: { ...FAKE_RECORD, end: DEFAULT_DATE.plus({ hours: 2 }) },
        model: { ...FAKE_MODEL, isDateHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("08:00 - 10:00\n(2 hours)");
});

test(`time duration: 1 minute diff`, async () => {
    await start({
        record: { ...FAKE_RECORD, end: DEFAULT_DATE.plus({ minutes: 1 }) },
        model: { ...FAKE_MODEL, isDateHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("08:00 - 08:01\n(1 minute)");
});

test(`time duration: 2 minutes diff`, async () => {
    await start({
        record: { ...FAKE_RECORD, end: DEFAULT_DATE.plus({ minutes: 2 }) },
        model: { ...FAKE_MODEL, isDateHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("08:00 - 08:02\n(2 minutes)");
});

test(`time duration: 3 hours and 15 minutes diff`, async () => {
    await start({
        model: { ...FAKE_MODEL, isDateHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("08:00 - 11:15\n(3 hours, 15 minutes)");
});

test(`isDateHidden is true`, async () => {
    await start({
        model: { ...FAKE_MODEL, isDateHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("08:00 - 11:15\n(3 hours, 15 minutes)");
});

test(`isDateHidden is false`, async () => {
    await start({
        model: { ...FAKE_MODEL, isDateHidden: false },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("July 16, 2021");
    expect(`.o_card_record > div:eq(1)`).toHaveText("08:00 - 11:15\n(3 hours, 15 minutes)");
});

test(`isTimeHidden is true`, async () => {
    await start({
        record: { ...FAKE_RECORD, isTimeHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("July 16, 2021");
});

test(`isTimeHidden is false`, async () => {
    await start({
        record: { ...FAKE_RECORD, isTimeHidden: false },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("July 16, 2021");
    expect(`.o_card_record > div:eq(1)`).toHaveText("08:00 - 11:15\n(3 hours, 15 minutes)");
});

test(`canDelete is true`, async () => {
    await start({
        model: { ...FAKE_MODEL, canDelete: true },
    });
    expect(`.o_cw_popover_delete`).toHaveCount(1);
});

test(`canDelete is false`, async () => {
    await start({
        model: { ...FAKE_MODEL, canDelete: false },
    });
    expect(`.o_cw_popover_delete`).toHaveCount(0);
});

test(`click on delete button`, async () => {
    await start({
        model: { ...FAKE_MODEL, canDelete: true },
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

describe("popover node", () => {
    test(`with only popover-body template`, async () => {
        await start({
            arch: `
                <calendar date_start="start">
                    <popover>
                        <templates>
                            <t t-name="popover-body">
                                <field name="partner_id"/>
                            </t>
                        </templates>
                    </popover>
                </calendar>
            `,
        });
        expect(`.o_popover_header`).toHaveCount(0);
        expect(`.o_popover_body`).toHaveCount(1);
        expect(`.o_popover_body`).toHaveText("Some partner");
        expect(`.o_popover_footer`).toHaveCount(1);
        expect(`.o_popover_footer .o_cw_popover_edit`).toHaveCount(1);
        expect(`.o_popover_footer .o_cw_popover_delete`).toHaveCount(1);
    });

    test(`without popover-body template`, async () => {
        await start({
            arch: `
                <calendar date_start="start">
                    <popover>
                        <templates>
                        </templates>
                    </popover>
                </calendar>
            `,
        });
        expect(`.o_popover_body`).toHaveCount(1);
        expect(`.o_popover_body`).toHaveText("July 16, 2021\n08:00 - 11:15\n(3 hours, 15 minutes)");
    });

    test(`with popover-footer template`, async () => {
        await start({
            arch: `
                <calendar date_start="start">
                    <popover>
                        <templates>
                            <t t-name="popover-footer">
                                <button class="btn btn-secondary o_custom_footer_button">Custom</button>
                            </t>
                        </templates>
                    </popover>
                </calendar>
            `,
        });
        expect(`.o_popover_footer .o_cw_popover_edit`).toHaveCount(0);
        expect(`.o_popover_footer .o_cw_popover_delete`).toHaveCount(0);
        expect(`.o_popover_footer .o_custom_footer_button`).toHaveCount(1);
    });

    test(`with popover-footer template and replace="0" attribute`, async () => {
        await start({
            arch: `
                <calendar date_start="start">
                    <popover>
                        <templates>
                            <t t-name="popover-footer" replace="0">
                                <button class="btn btn-secondary o_custom_footer_button">Custom</button>
                            </t>
                        </templates>
                    </popover>
                </calendar>
            `,
        });
        expect(`.o_popover_footer .o_cw_popover_edit`).toHaveCount(1);
        expect(`.o_popover_footer .o_cw_popover_delete`).toHaveCount(1);
        expect(`.o_popover_footer .o_custom_footer_button`).toHaveCount(1);
    });

    test(`with popover-header template`, async () => {
        await start({
            arch: `
                <calendar date_start="start">
                    <popover>
                        <templates>
                            <t t-name="popover-header">
                                <span class="o_custom_header">Custom Header</span>
                            </t>
                            <t t-name="popover-body">
                                Body
                            </t>
                        </templates>
                    </popover>
                </calendar>
            `,
        });
        expect(`.o_popover_header`).toHaveCount(1);
        expect(`.o_popover_header .o_custom_header`).toHaveCount(1);
        expect(`.o_popover_body`).toHaveText("Body");
    });

    test(`t-if using a field declared out of the template`, async () => {
        await start({
            arch: `
                <calendar date_start="start">
                    <popover>
                        <field name="partner_id"/>
                        <templates>
                            <t t-name="popover-header">
                                <span class="o_custom_header" t-if="record.partner_id.raw_value">
                                    header
                                </span>
                                <span class="not_displayed" t-if="!record.partner_id.raw_value">
                                    not displayed
                                </span>
                            </t>
                            <t t-name="popover-body">
                                <span class="o_custom_body">Body</span>
                                <span class="not_displayed" t-if="!record.partner_id.raw_value">
                                    not displayed
                                </span>
                            </t>
                            <t t-name="popover-footer">
                                <button class="btn btn-secondary o_custom_footer_button" t-if="record.partner_id.raw_value">
                                    footer button
                                </button>
                                <span class="not_displayed" t-if="!record.partner_id.raw_value">
                                    not displayed
                                </span>
                            </t>
                        </templates>
                    </popover>
                </calendar>
            `,
        });
        expect(`.o_popover_header .o_custom_header`).toHaveCount(1);
        expect(`.o_popover_body .o_custom_body`).toHaveCount(1);
        expect(`.o_popover_footer .o_custom_footer_button`).toHaveCount(1);
        expect(`.not_displayed`).toHaveCount(0);
    });

    test(`with card_id attribute`, async () => {
        await start({
            arch: `
                <calendar date_start="start">
                    <popover card_id="1"/>
                </calendar>
            `,
        });
        expect(`.o_popover_header`).toHaveCount(0);
        expect(`.o_popover_body .o_custom_card_body`).toHaveCount(1);
        expect(`.o_popover_body`).toHaveText("Meeting");
    });
});
