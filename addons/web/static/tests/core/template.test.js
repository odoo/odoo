import { after, expect, test } from "@odoo/hoot";
import { Component, useRef, xml } from "@odoo/owl";
import { mountWithCleanup, patchTranslations } from "@web/../tests/web_test_helpers";
import { registerTemplate, registerTemplateExtension } from "@web/core/templates";

function makeTemplate({ name, content, inheritFrom }) {
    return `<t t-name="${name}" ${inheritFrom ? `t-inherit="${inheritFrom}"` : ``}>${content}</t>`;
}

function makeTemplateExtension({ content, inheritFrom }) {
    return `<t t-inherit="${inheritFrom}" t-inherit-mode="extension">${content}</t>`;
}

function visit(node, addon, terms) {
    for (const { value } of node.attributes) {
        terms[value] = `${value} (${addon})`;
    }
    for (const childNode of node.childNodes) {
        if (childNode.nodeType === Node.TEXT_NODE) {
            const text = childNode.data.trim();
            terms[text] = `${text} (${addon})`;
        } else {
            visit(childNode, addon, terms);
        }
    }
}

const parser = new DOMParser();
function extractTranslations(template, addon) {
    const doc = parser.parseFromString(template, "text/xml");
    const root = doc.firstChild;
    const terms = {};
    visit(root, addon, terms);
    return terms;
}

function registerTemplates(...templates) {
    const translations = {};

    for (const { name, content, inheritFrom, inheritMode } of templates) {
        // we should avoid do twice makeTemplate/makeTemplateExtension
        const template =
            inheritMode === "extension"
                ? makeTemplateExtension({ content, inheritFrom })
                : makeTemplate({ name, content, inheritFrom });
        const addon = `addon_${name}`;
        const terms = extractTranslations(template, addon);
        translations[addon] = terms;
        after(
            inheritMode === "extension"
                ? registerTemplateExtension(inheritFrom, `/${addon}`, template)
                : registerTemplate(name, `/${addon}`, template)
        );
    }
    patchTranslations(translations);
}

async function mountTestComponentWithTemplate(name) {
    class TestComponent extends Component {
        static props = ["*"];
        static template = xml`<div t-ref="root"><t t-call="${name}"/></div>`;
        setup() {
            this.rootRef = useRef("root");
        }
    }
    const component = await mountWithCleanup(TestComponent);
    return component.rootRef.el;
}

test("translation-context: single template", async () => {
    registerTemplates({
        name: "A",
        content: `<div class="o_test_component" title="title">term</div>`,
    });
    const el = await mountTestComponentWithTemplate("A");
    expect(el).toHaveInnerHTML(`
        <div class="o_test_component" title="title (addon_A)">
            term (addon_A)
        </div>
    `);
});

test("translation-context: xpath position inside", async () => {
    registerTemplates(
        { name: "A", content: `<div class="o_test_component" title="title">term</div>` },
        {
            name: "B",
            content: `<xpath expr="div" position="inside"><span title="title">term</span></xpath>`,
            inheritFrom: "A",
        }
    );
    const el = await mountTestComponentWithTemplate("B");
    expect(el).toHaveInnerHTML(`
        <div class="o_test_component" title="title (addon_A)">
            term (addon_A)
            <span title="title (addon_B)">
                term (addon_B)
            </span>
        </div>
    `);
});

test("translation-context: xpath position attributes", async () => {
    registerTemplates(
        { name: "A", content: `<div class="o_test_component" title="title">term</div>` },
        {
            name: "B",
            content: `<xpath expr="div" position="attributes"><attribute name="title">title</attribute><attribute name="label">label</attribute></xpath>`,
            inheritFrom: "A",
        }
    );
    const el = await mountTestComponentWithTemplate("B");
    expect(el).toHaveInnerHTML(`
        <div class="o_test_component" title="title (addon_B)" label="label (addon_B)">
            term (addon_A)
        </div>
    `);
});

test("translation-context: xpath position after with some text", async () => {
    registerTemplates(
        {
            name: "A",
            content: `
                <div class="o_test_component" title="title">
                    <span>Hello</span>
                    <span>World</span>
                </div>
            `,
        },
        {
            name: "B",
            content: `<xpath expr="div/span" position="after"><div title="title">title</div>Text</xpath>`,
            inheritFrom: "A",
        }
    );
    const el = await mountTestComponentWithTemplate("B");
    expect(el).toHaveInnerHTML(`
        <div class="o_test_component" title="title (addon_A)">
            <span>Hello (addon_A)</span>
            <div title="title (addon_B)">title (addon_B)</div>
            Text (addon_B)
            <span>World (addon_A)</span>
        </div>
    `);
});

test("translation-context: xpath position inside: moved element", async () => {
    registerTemplates(
        {
            name: "A",
            content: `
                <div class="o_test_component">
                    <span>Hello</span>
                    <span>World</span>
                </div>
            `,
        },
        {
            name: "B",
            content: `
                <xpath expr="div/span" position="before">
                    <xpath expr="div/span[2]" position="move"/>
                </xpath>`,
            inheritFrom: "A",
        }
    );
    const el = await mountTestComponentWithTemplate("B");
    expect(el).toHaveInnerHTML(`
        <div class="o_test_component">
            <span>World (addon_A)</span>
            <span>Hello (addon_A)</span>
        </div>
    `);
});
