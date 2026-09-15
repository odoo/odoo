import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { registry } from "@web/core/registry";
import { Field } from "@web/views/fields/field";
import { Widget } from "@web/views/widgets/widget";

const viewWidgetRegistry = registry.category("view_widgets");

test("unknown <widget> arch node degrades to an empty widget instead of crashing", async () => {
    patchWithCleanup(console, {
        warn: (msg) => expect.step(`warn:${msg}`),
        info: (msg) => expect.step(`info:${msg}`),
    });
    const node = document.createElement("widget");
    node.setAttribute("name", "backend_only_widget");
    expect(viewWidgetRegistry.contains("backend_only_widget")).toBe(false);

    const widgetInfo = Widget.parseWidgetNode(node);
    expect.verifySteps(["info:Missing widget: backend_only_widget"]);
    expect(widgetInfo.name).toBe("backend_only_widget");
    expect(widgetInfo.widget.component.prototype).toBeInstanceOf(Component);
});

test("known <widget> arch node still resolves from the registry", async () => {
    class DummyWidget extends Component {
        static template = xml`<span>dummy</span>`;
        static props = ["*"];
    }
    viewWidgetRegistry.add("dummy_test_widget", { component: DummyWidget });

    const node = document.createElement("widget");
    node.setAttribute("name", "dummy_test_widget");
    node.setAttribute("title", "Some title");

    const widgetInfo = Widget.parseWidgetNode(node);
    expect(widgetInfo.widget.component).toBe(DummyWidget);
    expect(widgetInfo.attrs.title).toBe("Some title");
});

test("unknown field widget falls back to the field type widget without warning", async () => {
    patchWithCleanup(console, {
        warn: (msg) => expect.step(`warn:${msg}`),
        info: (msg) => expect.step(`info:${msg}`),
    });
    const models = { "fake.model": { fields: { partner_id: { type: "many2one", string: "P" } } } };
    const node = document.createElement("field");
    node.setAttribute("name", "partner_id");
    node.setAttribute("widget", "backend_only_field_widget");

    const fieldInfo = Field.parseFieldNode(node, models, "fake.model", "form");
    expect.verifySteps(["info:Missing widget: backend_only_field_widget"]);
    expect(fieldInfo.field).toBe(registry.category("fields").get("many2one"));
});

test("known field widget still resolves from the registry", async () => {
    patchWithCleanup(console, { warn: (msg) => expect.step(`warn:${msg}`) });
    const models = { "fake.model": { fields: { tag_ids: { type: "many2many", string: "T" } } } };
    const node = document.createElement("field");
    node.setAttribute("name", "tag_ids");
    node.setAttribute("widget", "many2many_tags");

    const fieldRegistry = registry.category("fields");
    const fieldInfo = Field.parseFieldNode(node, models, "fake.model", "form");
    expect.verifySteps([]);
    expect(fieldInfo.widget).toBe("many2many_tags");
    expect(fieldInfo.field).toBe(
        fieldRegistry.get("form.many2many_tags", fieldRegistry.get("many2many_tags"))
    );
});
