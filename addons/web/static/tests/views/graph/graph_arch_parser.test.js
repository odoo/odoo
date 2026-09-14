// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { parseXML } from "@web/core/utils/dom/xml";
import { GraphArchParser } from "@web/views/graph/graph_arch_parser";
import { elementToIR } from "@web/views/ir/view_ir";

describe.current.tags("headless");

const MODELS = {
    foo: {
        fields: {
            id: { type: "integer" },
            bar: { type: "boolean" },
            date: { type: "date" },
            revenue: { type: "float" },
            product_id: { type: "many2one" },
        },
    },
};

const ARCH = `
    <graph string="Revenue" type="line" order="desc" stacked="0" disable_linking="1">
        <field name="id"/>
        <field name="date" interval="month" string="When"/>
        <field name="product_id" invisible="1"/>
        <field name="bar" invisible="not context.get('x')" widget="boolean"/>
        <field name="revenue" type="measure"/>
    </graph>`;

const EXPECTED = {
    fields: MODELS.foo.fields,
    fieldAttrs: {
        date: { string: "When" },
        product_id: { isInvisible: true },
        bar: { invisible: "not context.get('x')", widget: "boolean" },
    },
    groupBy: ["date:month", "bar"],
    measures: ["revenue"],
    measure: "revenue",
    mode: "line",
    order: "DESC",
    title: "Revenue",
    stacked: false,
    disableLinking: true,
};

test("the graph parser consumes the IR", () => {
    expect(GraphArchParser.consumes).toBe("ir");
    const ir = elementToIR(parseXML(ARCH));
    expect(new GraphArchParser().parse(ir, MODELS, "foo")).toEqual(EXPECTED);
});

test("an element or a string still parses to the same archInfo", () => {
    const parser = new GraphArchParser();
    expect(parser.parse(parseXML(ARCH), MODELS, "foo")).toEqual(EXPECTED);
    expect(parser.parse(ARCH, MODELS, "foo")).toEqual(EXPECTED);
});

test("a field without a name is refused by kind", () => {
    expect(() =>
        new GraphArchParser().parse({ kind: "graph", children: [{ kind: "field" }] }),
    ).toThrow(/<field\/> requires a "name" attribute/);
});
