// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { parseXML } from "@web/core/utils/dom/xml";
import { elementToIR } from "@web/views/ir/view_ir";
import { ListArchParser } from "@web/views/list/list_arch_parser";

describe.current.tags("headless");

const MODELS = {
    foo: {
        fields: {
            id: { type: "integer", string: "ID" },
            name: { type: "char", string: "Name" },
            amount: { type: "float", string: "Amount" },
            sequence: { type: "integer", string: "Sequence" },
            partner_id: { type: "many2one", string: "Partner", relation: "partner" },
        },
    },
    partner: {
        fields: {
            id: { type: "integer", string: "ID" },
            display_name: { type: "char", string: "Display name" },
            city: { type: "char", string: "City" },
        },
    },
};

const ARCH = `
    <list string="Foos" editable="bottom" multi_edit="1" open_form_view="1" limit="20"
          count_limit="500" groups_limit="10" default_group_by="partner_id" no_open="1"
          expand="1" default_order="amount desc" export_xlsx="0" group_create="0"
          decoration-danger="amount &lt; 0" decoration-bf="name" class="o_foo_list"
          action="42" type="object" js_class="my_list">
        <header>
            <button name="validate" type="object" string="Validate" class="btn-primary"/>
            <field name="name"/>
        </header>
        <control>
            <create string="Add" context="{'default_name': 'x'}"/>
            <delete invisible="1"/>
            <button name="do_it" type="object" string="Do it"/>
        </control>
        <groupby name="partner_id">
            <field name="city"/>
            <button name="open_partner" type="object" string="Open"/>
        </groupby>
        <field name="sequence" widget="handle"/>
        <field name="name" class="fw-bold" optional="show" column_invisible="context.get('hide')"/>
        <field name="name" invisible="1"/>
        <button name="a" type="object" icon="fa-check" column_invisible="not name"/>
        <button name="b" type="object" icon="fa-times" column_invisible="not amount"/>
        <button name="c" type="object" icon="fa-eye" width="20px"/>
        <widget name="notification_alert" class="o_w"/>
        <field name="amount" sum="Total" decoration-danger="amount &lt; 0"/>
    </list>`;

/** @param {any} archInfo */
function comparable(archInfo) {
    const { xmlDoc, ...rest } = archInfo;
    return { rest, xml: xmlDoc.outerHTML };
}

test("the list parser consumes the IR and annotates its own copy", () => {
    expect(ListArchParser.consumes).toBe("ir");
    const ir = elementToIR(parseXML(ARCH));
    const parser = new ListArchParser();
    const archInfo = parser.parse(ir, MODELS, "foo");

    // the caller's tree is untouched: the annotations went on the parser's copy
    expect(JSON.stringify(ir)).not.toInclude("field_id");
    // the header's <field> is not a column: it stays unannotated, as before
    expect(
        archInfo.xmlDoc.querySelector("header field")?.hasAttribute("field_id"),
    ).toBe(false);
    expect(
        archInfo.xmlDoc
            .querySelector("list > field[name=name]")
            ?.getAttribute("field_id"),
    ).toBe("name_0");
    expect(archInfo.xmlDoc.querySelector("widget")?.getAttribute("widget_id")).toBe(
        "widget_1",
    );
    expect(
        archInfo.xmlDoc.querySelector("groupby field")?.getAttribute("field_id"),
    ).toBe("city_0");

    expect(Object.keys(archInfo.fieldNodes)).toEqual([
        "sequence_0",
        "name_0",
        "name_1",
        "amount_0",
    ]);
    expect(archInfo.columns.map((c) => c.type)).toEqual([
        "field",
        "field",
        "field",
        "button_group",
        "button_group",
        "widget",
        "field",
    ]);
    expect(archInfo.columns[1].className).toBe("fw-bold");
    expect(archInfo.columns[1].optional).toBe("show");
    expect(archInfo.columns[3].buttons.map((b) => b.clickParams.name)).toEqual([
        "a",
        "b",
    ]);
    expect(archInfo.columns[3].column_invisible).toBe("(not name) and (not amount)");
    expect(archInfo.columns[4].attrs).toEqual({ width: "20px" });
    expect(archInfo.headerButtons.map((b) => b.clickParams.name)).toEqual(["validate"]);
    expect(archInfo.controls.map((c) => c.type)).toEqual([
        "create",
        "delete",
        "button",
    ]);
    expect(archInfo.controls[0]).toEqual({
        type: "create",
        context: "{'default_name': 'x'}",
        string: "Add",
        invisible: null,
        class: null,
    });
    expect(Object.keys(archInfo.groupBy.fields.partner_id.fieldNodes)).toEqual([
        "city_0",
    ]);
    expect(archInfo.groupBy.buttons.partner_id.map((b) => b.clickParams.name)).toEqual([
        "open_partner",
    ]);
    expect(archInfo.activeActions).toEqual({
        type: "view",
        edit: true,
        create: true,
        delete: true,
        duplicate: true,
        exportXlsx: false,
        createGroup: false,
        editGroup: true,
        deleteGroup: true,
    });
    expect(archInfo.editable).toBe("bottom");
    expect(archInfo.multiEdit).toBe(true);
    expect(archInfo.openFormView).toBe(true);
    expect(archInfo.defaultGroupBy).toEqual(["partner_id"]);
    expect(archInfo.limit).toBe(20);
    expect(archInfo.countLimit).toBe(500);
    expect(archInfo.groupsLimit).toBe(10);
    expect(archInfo.noOpen).toBe(true);
    expect(archInfo.rawExpand).toBe("1");
    expect(archInfo.className).toBe("o_foo_list");
    expect(archInfo.decorations).toEqual([
        { class: "text-danger", condition: "amount < 0" },
        { class: "fw-bold", condition: "name" },
    ]);
    expect(archInfo.defaultOrder).toEqual([{ name: "amount", asc: false }]);
    expect(archInfo.openAction).toEqual({ action: "42", type: "object" });

    // the walk's parent map covers every node the parser visited
    expect(parser.parents.size).toBeGreaterThan(10);
});

test("an element or a string still parses to the same archInfo, xmlDoc included", () => {
    const parser = new ListArchParser();
    const fromIR = comparable(parser.parse(elementToIR(parseXML(ARCH)), MODELS, "foo"));
    expect(comparable(parser.parse(parseXML(ARCH), MODELS, "foo"))).toEqual(fromIR);
    expect(comparable(parser.parse(ARCH, MODELS, "foo"))).toEqual(fromIR);
});

test("a handle field orders the list when the arch gives no order", () => {
    const archInfo = new ListArchParser().parse(
        `<list><field name="sequence" widget="handle"/><field name="name"/></list>`,
        MODELS,
        "foo",
    );
    expect(archInfo.defaultOrder).toEqual([
        { name: "sequence", asc: true },
        { name: "id", asc: true },
    ]);
    expect(archInfo.limit).toBe(null);
    expect(archInfo.defaultGroupBy).toBe(null);
    expect(archInfo.openAction).toBe(null);
});
