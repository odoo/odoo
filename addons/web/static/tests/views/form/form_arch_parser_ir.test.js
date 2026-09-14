// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { parseXML } from "@web/core/utils/dom/xml";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { elementToIR } from "@web/views/ir/view_ir";

describe.current.tags("headless");

const MODELS = {
    partner: {
        fields: {
            id: { type: "integer", string: "ID" },
            name: { type: "char", string: "Name" },
            email: { type: "char", string: "Email" },
            props: { type: "properties", string: "Properties" },
            child_ids: { type: "one2many", string: "Children", relation: "partner" },
        },
    },
};

const ARCH = `
    <form create="0" disable_autofocus="1" js_class="my_form" string="Partner">
        <header><button name="go" type="object" string="Go"/></header>
        <sheet>
            <group>
                <field name="name" default_focus="1"/>
                <field name="email" widget="email" invisible="not name"/>
                <widget name="notification_alert"/>
            </group>
            <notebook>
                <page string="Children">
                    <field name="child_ids" mode="list">
                        <list><field name="name"/><field name="email"/></list>
                        <form><field name="name"/></form>
                    </field>
                </page>
                <page string="Props">
                    <field name="props"/>
                </page>
            </notebook>
        </sheet>
    </form>`;

/** @param {any} archInfo */
function comparable(archInfo) {
    const { xmlDoc, ...rest } = archInfo;
    return { rest, xml: xmlDoc.outerHTML };
}

test("the form parser consumes the IR and annotates its own copy", () => {
    expect(FormArchParser.consumes).toBe("ir");
    const ir = elementToIR(parseXML(ARCH));
    const parser = new FormArchParser();
    const archInfo = parser.parse(ir, MODELS, "partner");

    expect(JSON.stringify(ir)).not.toInclude("field_id");
    expect(Object.keys(archInfo.fieldNodes)).toEqual([
        "name_0",
        "email_0",
        "child_ids_0",
        "props_0",
    ]);
    expect(
        archInfo.xmlDoc.querySelector("field[name=email]")?.getAttribute("field_id"),
    ).toBe("email_0");
    expect(archInfo.xmlDoc.querySelector("widget")?.getAttribute("widget_id")).toBe(
        "widget_1",
    );
    // the sub-view's own annotation stays inside the sub-view's parse
    expect(
        archInfo.xmlDoc
            .querySelector("field[name=child_ids] list field")
            ?.hasAttribute("field_id"),
    ).toBe(false);
    expect(Object.keys(archInfo.fieldNodes.child_ids_0.views)).toEqual([
        "list",
        "form",
    ]);
    expect(archInfo.fieldNodes.child_ids_0.viewMode).toBe("list");
    expect(
        archInfo.fieldNodes.child_ids_0.views.list.columns.map((c) => c.name),
    ).toEqual(["name", "email"]);
    expect(archInfo.fieldNodes.email_0.invisible).toBe("not name");
    expect(archInfo.autofocusFieldIds).toEqual(["name_0"]);
    expect(archInfo.disableAutofocus).toBe(true);
    expect(archInfo.activeActions).toEqual({
        type: "view",
        create: false,
        edit: true,
        delete: true,
        duplicate: false,
        addPropertyFieldValue: true,
    });
    expect(Object.keys(archInfo.widgetNodes)).toEqual(["widget_1"]);
    expect(parser.parents.get(ir)).toBe(undefined);
    expect(parser.parents.size).toBeGreaterThan(10);
});

test("an element or a string still parses to the same archInfo, xmlDoc included", () => {
    const parser = new FormArchParser();
    const fromIR = comparable(
        parser.parse(elementToIR(parseXML(ARCH)), MODELS, "partner"),
    );
    // sub-view archInfos carry their own xmlDoc; compare those by markup too
    const flatten = (/** @type {any} */ c) => {
        for (const fieldInfo of Object.values(c.rest.fieldNodes)) {
            for (const view of Object.values(
                /** @type {any} */ (fieldInfo).views || {},
            )) {
                if (view.xmlDoc) {
                    view.xml = view.xmlDoc.outerHTML;
                    delete view.xmlDoc;
                }
            }
        }
        return c;
    };
    flatten(fromIR);
    expect(
        flatten(comparable(parser.parse(parseXML(ARCH), MODELS, "partner"))),
    ).toEqual(fromIR);
    expect(flatten(comparable(parser.parse(ARCH, MODELS, "partner")))).toEqual(fromIR);
});
