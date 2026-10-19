import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { defineModels, fields, models, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { DEFAULT_DATE, FAKE_FIELDS } from "./calendar_test_helpers";

import { createElement, parseXML } from "@web/core/utils/xml";
import { CalendarArchParser } from "@web/views/calendar/calendar_arch_parser";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { Field } from "@web/views/fields/field";

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
};

/**
 * `getDefaultPopoverBody`'s retro-compatibility layer renders any field
 * declared directly in the arch (outside of `<popover>`) as a `popoverFieldNodes`
 * entry on the model's meta. Build one the same way `CalendarArchParser` does,
 * so a default (no custom `<popover>` arch) popover still shows an extra field,
 * exactly like a view declaring `<field name="description"/>` would.
 */
const DEFAULT_POPOVER_FIELD_NODES = {
    description: Field.parseFieldNode(
        createElement("field", { name: "description" }),
        { event: { fields: FAKE_FIELDS } },
        "event",
        "calendar"
    ),
};

const DEFAULT_MODEL = {
    resModel: "event",
    canEdit: true,
    canDelete: true,
    isDateHidden: false,
    load() {},
    meta: {
        fields: FAKE_FIELDS,
        context: {},
        popoverFieldNodes: DEFAULT_POPOVER_FIELD_NODES,
    },
};

const FAKE_PROPS = {
    openRecord() {},
    deleteRecord() {},
    close() {},
};

async function start({ arch, model = DEFAULT_MODEL, record = FAKE_RECORD, ...props } = {}) {
    let popoverNode = model.meta.popoverNode;
    let popoverFieldNodes = model.meta.popoverFieldNodes;
    if (arch) {
        ({ popoverNode, popoverFieldNodes } = new CalendarArchParser().parse(
            parseXML(arch),
            { fake: { fields: FAKE_FIELDS } },
            "fake"
        ));
    }
    await mountWithCleanup(CalendarCommonPopover, {
        props: {
            ...FAKE_PROPS,
            ...props,
            model: { ...model, meta: { ...model.meta, popoverNode, popoverFieldNodes } },
            record,
        },
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
        model: { ...DEFAULT_MODEL, isDateHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("08:00 - 09:00\n(1 hour)");
});

test(`time duration: 2 hours diff`, async () => {
    await start({
        record: { ...FAKE_RECORD, end: DEFAULT_DATE.plus({ hours: 2 }) },
        model: { ...DEFAULT_MODEL, isDateHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("08:00 - 10:00\n(2 hours)");
});

test(`time duration: 1 minute diff`, async () => {
    await start({
        record: { ...FAKE_RECORD, end: DEFAULT_DATE.plus({ minutes: 1 }) },
        model: { ...DEFAULT_MODEL, isDateHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("08:00 - 08:01\n(1 minute)");
});

test(`time duration: 2 minutes diff`, async () => {
    await start({
        record: { ...FAKE_RECORD, end: DEFAULT_DATE.plus({ minutes: 2 }) },
        model: { ...DEFAULT_MODEL, isDateHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("08:00 - 08:02\n(2 minutes)");
});

test(`time duration: 3 hours and 15 minutes diff`, async () => {
    await start({
        model: { ...DEFAULT_MODEL, isDateHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("08:00 - 11:15\n(3 hours, 15 minutes)");
});

test(`isDateHidden is true`, async () => {
    await start({
        model: { ...DEFAULT_MODEL, isDateHidden: true },
    });
    expect(`.o_card_record > div:eq(0)`).toHaveText("08:00 - 11:15\n(3 hours, 15 minutes)");
});

test(`isDateHidden is false`, async () => {
    await start({
        model: { ...DEFAULT_MODEL, isDateHidden: false },
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
        model: { ...DEFAULT_MODEL, canDelete: true },
    });
    expect(`.o_cw_popover_delete`).toHaveCount(1);
});

test(`canDelete is false`, async () => {
    await start({
        model: { ...DEFAULT_MODEL, canDelete: false },
    });
    expect(`.o_cw_popover_delete`).toHaveCount(0);
});

test(`click on delete button`, async () => {
    await start({
        model: { ...DEFAULT_MODEL, canDelete: true },
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

test(`popover node with default body and footer`, async () => {
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
    expect(`.o_popover_footer .o_cw_popover_edit`).toHaveCount(1);
    expect(`.o_popover_footer .o_cw_popover_delete`).toHaveCount(1);
});
