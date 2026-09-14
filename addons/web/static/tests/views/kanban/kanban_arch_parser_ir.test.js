// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { parseXML } from "@web/core/utils/dom/xml";
import { elementToIR } from "@web/views/ir/view_ir";
import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";

describe.current.tags("headless");

const MODELS = {
    foo: {
        fields: {
            id: { type: "integer", string: "ID" },
            name: { type: "char", string: "Name" },
            state: { type: "selection", string: "State" },
            sequence: { type: "integer", string: "Sequence" },
            amount: { type: "float", string: "Amount" },
            tag_ids: { type: "many2many", string: "Tags", relation: "tag" },
            partner_id: { type: "many2one", string: "Partner", relation: "partner" },
        },
    },
    tag: { fields: { id: { type: "integer", string: "ID" } } },
    partner: { fields: { id: { type: "integer", string: "ID" } } },
};

const ARCH = `
    <kanban default_group_by="partner_id" default_order="amount desc" limit="30" count_limit="300"
            records_draggable="0" archivable="0" quick_create="0" on_create="quick_create"
            quick_create_view="foo.quick" highlight_color="state" examples="foo_examples"
            class="o_foo_kanban" action="42" type="object" js_class="my_kanban">
        <header>
            <button name="validate" type="object" string="Validate"/>
        </header>
        <control>
            <create string="Add"/>
        </control>
        <progressbar field="state" colors='{"done": "success"}' sum_field="amount" help="Progress"/>
        <field name="sequence" widget="handle"/>
        <field name="partner_id" options="{'group_by_tooltip': {'name': 'Name'}}"/>
        <templates>
            <t t-name="card">
                <field name="name"/>
                <field name="tag_ids"/>
                <widget name="notification_alert"/>
                <img t-att-src="kanban_image('foo', 'image', record.id.raw_value)"/>
            </t>
            <t t-name="menu">
                <a>Menu</a>
            </t>
        </templates>
    </kanban>`;

/** @param {any} archInfo */
function comparable(archInfo) {
    const { xmlDoc, templateDocs, ...rest } = archInfo;
    return {
        rest,
        xml: xmlDoc.outerHTML,
        templates: Object.fromEntries(
            Object.entries(templateDocs).map(([name, doc]) => [name, doc.outerHTML]),
        ),
    };
}

test("the kanban parser consumes the IR and annotates its own copy", () => {
    expect(KanbanArchParser.consumes).toBe("ir");
    const ir = elementToIR(parseXML(ARCH));
    const parser = new KanbanArchParser();
    const archInfo = parser.parse(ir, MODELS, "foo");

    expect(JSON.stringify(ir)).not.toInclude("field_id");
    expect(Object.keys(archInfo.templateDocs)).toEqual(["card", "menu"]);
    const card = archInfo.templateDocs.card;
    expect(card.ownerDocument).toBe(archInfo.xmlDoc.ownerDocument);
    expect(card.querySelector("field[name=name]")?.getAttribute("field_id")).toBe(
        "name_0",
    );
    // a many2many without a widget is drawn as tags, and the compiler reads that off the tree
    expect(card.querySelector("field[name=tag_ids]")?.getAttribute("widget")).toBe(
        "many2many_tags",
    );
    expect(card.querySelector("widget")?.getAttribute("widget_id")).toBe("widget_1");
    expect(Object.keys(archInfo.fieldNodes)).toEqual([
        "sequence_0",
        "partner_id_0",
        "name_0",
        "tag_ids_0",
        "write_date_0",
    ]);
    expect(archInfo.fieldNodes.tag_ids_0.widget).toBe("many2many_tags");
    expect(archInfo.handleField).toBe("sequence");
    expect(archInfo.tooltipInfo).toEqual({ partner_id: { name: "Name" } });
    expect(archInfo.headerButtons.map((b) => b.clickParams.name)).toEqual(["validate"]);
    expect(archInfo.controls).toEqual([
        { type: "create", context: null, string: "Add", invisible: null, class: null },
    ]);
    expect(archInfo.progressAttributes).toEqual({
        fieldName: "state",
        colors: { done: "success" },
        sumField: MODELS.foo.fields.amount,
        help: "Progress",
    });
    expect(archInfo.activeActions).toEqual({
        type: "view",
        edit: true,
        create: true,
        delete: true,
        duplicate: true,
        archiveGroup: false,
        createGroup: true,
        deleteGroup: true,
        editGroup: true,
        quickCreate: false,
    });
    expect(archInfo.className).toBe("o_foo_kanban");
    expect(archInfo.cardClassName).toBe("");
    expect(archInfo.cardColorField).toBe("state");
    expect(archInfo.canOpenRecords).toBe(true);
    expect(archInfo.defaultOrder).toEqual([{ name: "amount", asc: false }]);
    expect(archInfo.limit).toBe(30);
    expect(archInfo.countLimit).toBe(300);
    expect(archInfo.recordsDraggable).toBe(false);
    expect(archInfo.groupsDraggable).toBe(true);
    expect(archInfo.defaultGroupBy).toEqual(["partner_id"]);
    expect(archInfo.onCreate).toBe("quick_create");
    expect(archInfo.quickCreateView).toBe("foo.quick");
    expect(archInfo.openAction).toEqual({ action: "42", type: "object" });
    expect(archInfo.examples).toBe("foo_examples");
    expect(parser.parents.get(ir)).toBe(undefined);
    expect(parser.parents.size).toBeGreaterThan(10);
});

test("an element or a string still parses to the same archInfo, templates included", () => {
    const parser = new KanbanArchParser();
    const fromIR = comparable(parser.parse(elementToIR(parseXML(ARCH)), MODELS, "foo"));
    expect(comparable(parser.parse(parseXML(ARCH), MODELS, "foo"))).toEqual(fromIR);
    expect(comparable(parser.parse(ARCH, MODELS, "foo"))).toEqual(fromIR);
});

test("a kanban without a card template is refused, and a handle orders the cards", () => {
    const parser = new KanbanArchParser();
    expect(() => parser.parse(`<kanban><templates/></kanban>`, MODELS, "foo")).toThrow(
        "Missing 'card' template.",
    );
    const archInfo = parser.parse(
        `<kanban><field name="sequence" widget="handle"/><templates><t t-name="card"/></templates></kanban>`,
        MODELS,
        "foo",
    );
    expect(archInfo.defaultOrder).toEqual([
        { name: "sequence", asc: true },
        { name: "id", asc: true },
    ]);
    expect(archInfo.progressAttributes).toBe(false);
    expect(archInfo.limit).toBe(null);
    expect(archInfo.onCreate).toBe(null);
    expect(archInfo.examples).toBe(null);
});
