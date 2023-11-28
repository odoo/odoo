/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { getFixture, mount, nextTick } from "@web/../tests/helpers/utils";
import { Editor } from "@web/core/editors/editor";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { setupViewRegistries } from "../views/helpers";

let serverData;
let target;

async function mountEditor(params) {
    const props = { ...params };
    const mockRPC = props.mockRPC;
    delete props.mockRPC;

    class Parent extends Component {
        setup() {
            this.editorProps = {
                ...props,
                update: (value) => {
                    if (props.update) {
                        props.update(value);
                    }
                    this.editorProps.value = value;
                    this.render();
                },
            };
        }
        async set(value) {
            this.editorProps.value = value;
            this.render();
            await nextTick();
        }
    }
    Parent.components = { Editor };
    Parent.template = xml`<Editor t-props="editorProps"/>`;

    const env = await makeTestEnv({ serverData, mockRPC });
    await mount(MainComponentsContainer, target, { env });
    return mount(Parent, target, { env, props });
}

QUnit.module("Editor", {
    beforeEach() {
        serverData = {
            models: {
                partner: {
                    fields: {},
                    records: [
                        { id: 1, display_name: "John" },
                        { id: 3, display_name: "Luke" },
                    ],
                },
            },
            views: {
                "partner,false,list": `<list><field name="display_name"/></list>`,
                "partner,false,search": `<search/>`,
            },
        };
        target = getFixture();
        setupViewRegistries();
    },
});

QUnit.test("integer: simple rendering (valid case)", async (assert) => {
    await mountEditor({ type: "integer", value: 1 });
    assert.ok(true);
});

QUnit.test("integer: simple rendering (invalid case)", async (assert) => {
    await mountEditor({ type: "integer", value: "a" });
    assert.ok(true);
});

QUnit.test("[integer]: simple rendering", async (assert) => {
    await mountEditor({ type: "list", subType: "integer", value: [1, 2, "a"] });
    assert.ok(true);
});

QUnit.test("[integer]: simple rendering (invalid case)", async (assert) => {
    await mountEditor({ type: "list", subType: "integer", value: 1 });
    assert.ok(true);
});

QUnit.test("integer -> integer: simple rendering range", async (assert) => {
    await mountEditor({ type: "range", subType: "integer", value: [1, 2] });
    assert.ok(true);
});

QUnit.test("integer -> integer: simple rendering (invalid case)", async (assert) => {
    await mountEditor({ type: "range", subType: "integer", value: [1] });
    assert.ok(true);
});

QUnit.test("id: simple rendering", async (assert) => {
    await mountEditor({ type: "id", value: 1, resModel: "partner" });
    assert.ok(true);
});

QUnit.test("id: simple rendering", async (assert) => {
    await mountEditor({ type: "id", value: "a", resModel: "partner" });
    assert.ok(true);
});

QUnit.test("[id] simple rendering", async (assert) => {
    await mountEditor({ type: "list", subType: "id", value: [1, 2], resModel: "partner" });
    assert.ok(true);
});

QUnit.test("[id] simple rendering", async (assert) => {
    await mountEditor({ type: "list", subType: "id", value: 1, resModel: "partner" });
    assert.ok(true);
});

QUnit.test("id -> id: simple rendering range", async (assert) => {
    await mountEditor({ type: "range", subType: "id", value: [1, 2], resModel: "partner" });
    assert.ok(true);
});

QUnit.test("id -> id: simple rendering (invalid case)", async (assert) => {
    await mountEditor({ type: "range", subType: "id", value: [1], resModel: "partner" });
    assert.ok(true);
});
