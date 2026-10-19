import { expect, test } from "@odoo/hoot";
import { registerPythonTemplate } from "@point_of_sale/app/utils/convert_python_template";
import { getTemplate } from "@web/core/templates";

let nextId = 0;
function registerAndParse(templateString) {
    const name = `test.convert_python_template_${nextId++}`;
    const unregister = registerPythonTemplate(name, "", templateString);
    return { template: getTemplate(name), unregister };
}

test("does not duplicate the closing '>' when t-key is already present on a self-closing t-foreach node", () => {
    const { template, unregister } = registerAndParse(
        `<div><p t-esc="item" t-foreach="items" t-as="item" t-key="item_index"/></div>`
    );
    expect(template.outerHTML).not.toInclude(">>");
    expect(template.querySelector("p").getAttribute("t-key")).toBe("item_index");
    unregister();
});

test("does not duplicate the closing '>' when t-key is already present on an open/close t-foreach node", () => {
    const { template, unregister } = registerAndParse(
        `<div><t t-foreach="items" t-as="item" t-key="item_index"><p t-esc="item"/></t></div>`
    );
    expect(template.outerHTML).not.toInclude(">>");
    unregister();
});

test("adds a t-key on an open/close t-foreach node when missing", () => {
    const { template, unregister } = registerAndParse(
        `<div><t t-foreach="items" t-as="item"><p t-esc="item"/></t></div>`
    );
    expect(template.querySelector("t").getAttribute("t-key")).toBe("item_index");
    unregister();
});

test("adds a t-key on a self-closing t-foreach node when missing, without breaking the tag", () => {
    const { template, unregister } = registerAndParse(
        `<div><p t-esc="item" t-foreach="items" t-as="item"/></div>`
    );
    expect(template.outerHTML).not.toInclude("parsererror");
    expect(template.querySelector("p").getAttribute("t-key")).toBe("item_index");
    unregister();
});
