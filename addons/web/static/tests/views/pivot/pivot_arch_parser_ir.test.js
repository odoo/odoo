// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { parseXML } from "@web/core/utils/dom/xml";
import { elementToIR } from "@web/views/ir/view_ir";
import { PivotArchParser } from "@web/views/pivot/pivot_arch_parser";

describe.current.tags("headless");

const ARCH = `
    <pivot string="Analysis" default_order="date desc" disable_linking="1" display_quantity="0">
        <field name="date" interval="month" type="row" widget="date_only"/>
        <field name="product_id" type="col" string="Product" options="{'no_open': True}"/>
        <field name="revenue" type="measure"/>
        <field name="qty" operator="sum" foo="bar"/>
        <field name="hidden" invisible="1" type="row"/>
    </pivot>`;

const EXPECTED = {
    activeMeasures: ["revenue", "qty"],
    colGroupBys: ["product_id"],
    defaultOrder: "date desc",
    fieldAttrs: {
        date: {},
        product_id: { string: "Product", options: { no_open: true } },
        revenue: {},
        qty: { foo: "bar" },
        hidden: { isInvisible: true },
    },
    rowGroupBys: ["date:month"],
    widgets: { "date:month": "date_only" },
    title: "Analysis",
    disableLinking: true,
    displayQuantity: false,
};

test("the pivot parser consumes the IR", () => {
    expect(PivotArchParser.consumes).toBe("ir");
    expect(new PivotArchParser().parse(elementToIR(parseXML(ARCH)))).toEqual(EXPECTED);
});

test("an element or a string still parses to the same archInfo", () => {
    const parser = new PivotArchParser();
    expect(parser.parse(parseXML(ARCH))).toEqual(EXPECTED);
    expect(parser.parse(ARCH)).toEqual(EXPECTED);
});
