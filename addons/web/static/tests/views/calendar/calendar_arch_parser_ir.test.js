// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { parseXML } from "@web/core/utils/dom/xml";
import { CalendarArchParser } from "@web/views/calendar/calendar_arch_parser";
import { parseFieldNode } from "@web/views/field_arch";
import { elementToIR } from "@web/views/ir/view_ir";

import { FAKE_FIELDS } from "./calendar_test_helpers.js";

describe.current.tags("headless");

const MODELS = {
    fake: { fields: FAKE_FIELDS },
    partner: { fields: { name: { string: "Name", type: "char" } } },
};

const ARCH = `
    <calendar date_start="start" date_stop="stop" date_delay="delay" all_day="allday"
              color="color" create_name_field="name" aggregate="delay:sum"
              mode="month" scales="week,month" quick_create="1" quick_create_view_id="7"
              form_view_id="3" event_limit="4" event_open_popup="1" hide_date="1"
              show_unusual_days="1" js_class="my_calendar" create="0">
        <field name="user_id" avatar_field="avatar" write_model="filter" write_field="user_id"
               filter_field="is_checked" filters="1" color="color"/>
        <field name="partner_id" invisible="1"/>
        <field name="description" invisible="1" filters="1"/>
        <field name="name"/>
    </calendar>`;

test("the calendar parser consumes the IR", () => {
    expect(CalendarArchParser.consumes).toBe("ir");
    const parser = new CalendarArchParser();
    const fromIR = parser.parse(elementToIR(parseXML(ARCH)), MODELS, "fake");

    expect(fromIR.fieldMapping).toEqual({
        date_start: "start",
        date_stop: "stop",
        date_delay: "delay",
        all_day: "allday",
        color: "color",
        create_name_field: "name",
    });
    // root attributes in FIELD_ATTRIBUTE_NAMES order, then the field nodes
    expect(fromIR.fieldNames).toEqual([
        "start",
        "delay",
        "stop",
        "allday",
        "name",
        "color",
        "user_id",
        "partner_id",
        "description",
    ]);
    expect(fromIR.aggregate).toBe("delay:sum");
    expect(fromIR.scale).toBe("month");
    expect(fromIR.scales).toEqual(["week", "month"]);
    expect(fromIR.quickCreateViewId).toBe(7);
    expect(fromIR.formViewId).toBe(3);
    expect(fromIR.eventLimit).toBe(4);
    expect(fromIR.hasEditDialog).toBe(true);
    expect(fromIR.isDateHidden).toBe(true);
    expect(fromIR.showUnusualDays).toBe(true);
    expect(fromIR.canCreate).toBe(false);
    expect(Object.keys(fromIR.filtersInfo)).toEqual(["user_id", "description"]);
    expect(fromIR.filtersInfo.user_id).toEqual({
        avatarFieldName: "avatar",
        colorFieldName: "color",
        context: "{}",
        fieldName: "user_id",
        filterFieldName: "is_checked",
        label: "User",
        resModel: "user",
        writeFieldName: "user_id",
        writeResModel: "filter",
    });
    expect(Object.keys(fromIR.popoverFieldNodes)).toEqual([
        "user_id",
        "partner_id",
        "description",
        "name",
    ]);
    expect(fromIR.popoverFieldNodes.partner_id.invisible).toBe("1");
});

test("an element or a string still parses to the same archInfo", () => {
    const parser = new CalendarArchParser();
    const fromIR = parser.parse(elementToIR(parseXML(ARCH)), MODELS, "fake");
    expect(parser.parse(parseXML(ARCH), MODELS, "fake")).toEqual(fromIR);
    expect(parser.parse(ARCH, MODELS, "fake")).toEqual(fromIR);
});

test("parseFieldNode reads an IR node and an element alike, sub-views included", () => {
    const field = `
        <field name="partner_ids" widget="many2many_tags" string="Guests" on_change="1"
               options="{'no_create': True}" decoration-danger="not name" readonly="0"
               data-tooltip="x" t-att-class="ignored" mode="list,kanban">
            <list><field name="name"/></list>
            <kanban><templates><t t-name="card"><field name="name"/></t></templates></kanban>
        </field>`;
    const element = parseXML(field);
    const fromElement = parseFieldNode(element, MODELS, "fake", "form");
    const fromIR = parseFieldNode(elementToIR(element), MODELS, "fake", "form");

    expect(fromIR.name).toBe("partner_ids");
    expect(fromIR.widget).toBe("many2many_tags");
    expect(fromIR.string).toBe("Guests");
    expect(fromIR.onChange).toBe(true);
    expect(fromIR.options).toEqual({ no_create: true });
    expect(fromIR.decorations).toEqual({ danger: "not name" });
    expect(fromIR.readonly).toBe("0");
    expect(fromIR.attrs).toEqual({
        "data-tooltip": "x",
        mode: "list,kanban",
        readonly: "0",
    });
    // `default` is the widget's relatedFields view; list and kanban are the sub-archs
    expect(Object.keys(fromIR.views)).toEqual(["default", "list", "kanban"]);
    expect(fromIR.views.list.columns.map((c) => c.name)).toEqual(["name"]);

    // `field` is a registry entry, compared by identity
    expect(fromIR.field).toBe(fromElement.field);
    expect({ ...fromIR, field: null, views: null }).toEqual({
        ...fromElement,
        field: null,
        views: null,
    });
    expect(Object.keys(fromElement.views)).toEqual(["default", "list", "kanban"]);
    expect(fromIR.views.list.columns.map((c) => c.name)).toEqual(
        fromElement.views.list.columns.map((c) => c.name),
    );
});
