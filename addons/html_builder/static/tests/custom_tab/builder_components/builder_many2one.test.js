import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent, useGetItemValue } from "@html_builder/core/utils";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { xml } from "@odoo/owl";
import { contains, defineModels, fields, models, onRpc } from "@web/../tests/web_test_helpers";

class Test extends models.Model {
    _name = "test";
    _records = [
        { id: 1, name: "First" },
        { id: 2, name: "Second" },
        { id: 3, name: "Third" },
    ];
    name = fields.Char();
}

describe.current.tags("desktop");
defineModels([Test]);

test("many2one: async load", async () => {
    const defWillLoad = new Deferred();
    const defDidApply = new Deferred();
    onRpc("test", "name_search", () => [
        [1, "First"],
        [2, "Second"],
        [3, "Third"],
    ]);
    addBuilderAction({
        testAction: class extends BuilderAction {
            static id = "testAction";
            setup() {
                this.preview = false;
            }
            async load({ value }) {
                expect.step("load");
                await defWillLoad;
                return value;
            }
            apply({ editingElement, value }) {
                editingElement.dataset.test = value;
                defDidApply.resolve();
            }
            getValue({ editingElement }) {
                return editingElement.dataset.test;
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderMany2One action="'testAction'" model="'test'" limit="10"/>`;
        }
    );
    const { getEditableContent } = await setupHTMLBuilder(
        `<div class="test-options-target">b</div>`
    );
    const editableContent = getEditableContent();

    await contains(":iframe .test-options-target").click();

    await contains(".btn.o-dropdown").click();
    expect("input").toHaveCount(1);
    await contains("input").click();
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(3);
    await contains("span.o-dropdown-item").click();
    expect.verifySteps(["load"]);
    expect(editableContent).toHaveInnerHTML(`<div class="test-options-target">b</div>`);
    defWillLoad.resolve();
    await defDidApply;
    expect(editableContent).toHaveInnerHTML(
        `<div class="test-options-target" data-test="{&quot;id&quot;:1,&quot;display_name&quot;:&quot;First&quot;,&quot;name&quot;:&quot;First&quot;}">b</div>`
    );
});

test("dependency definition should not be outdated", async () => {
    onRpc("test", "name_search", () => [
        [1, "First"],
        [2, "Second"],
        [3, "Third"],
    ]);
    addBuilderAction({
        testAction: class extends BuilderAction {
            static id = "testAction";
            apply({ editingElement, value }) {
                editingElement.dataset.test = value;
            }
            getValue({ editingElement }) {
                return editingElement.dataset.test;
            }
        },
    });
    class TestMany2One extends BaseOptionComponent {
        static selector = ".test-options-target";
        static template = xml`
            <BuilderMany2One action="'testAction'" model="'test'" limit="10" id="'test_many2one_opt'"/>
            <BuilderRow t-if="getItemValueJSON('test_many2one_opt')?.id === 2"><span>Dependant</span></BuilderRow>
        `;
        setup() {
            super.setup();
            this.getItemValue = useGetItemValue();
        }
        getItemValueJSON(id) {
            const value = this.getItemValue(id);
            return value && JSON.parse(value);
        }
    }
    addBuilderOption(TestMany2One);
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);

    await contains(":iframe .test-options-target").click();

    await contains(".btn.o-dropdown").click();
    await contains("span.o-dropdown-item:contains(First)").click();
    expect("span:contains(Dependant)").toHaveCount(0);

    await contains(".btn.o-dropdown").click();
    await contains("span.o-dropdown-item:contains(Second)").click();
    expect("span:contains(Dependant)").toHaveCount(1);

    await contains(".btn.o-dropdown").click();
    await contains("span.o-dropdown-item:contains(Third)").click();
    expect("span:contains(Dependant)").toHaveCount(0);
});

test("BuilderMany2One: add null_text option in website builder dropdown", async () => {
    onRpc("test", "name_search", () => [
        [1, "First"],
        [2, "Second"],
        [3, "Third"],
    ]);
    addBuilderAction({
        testAction: class extends BuilderAction {
            static id = "testAction";
            apply({ editingElement, value }) {
                editingElement.textContent = JSON.parse(value).name;
                editingElement.dataset.test = value;
            }
            getValue({ editingElement }) {
                return editingElement.dataset.test;
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderMany2One action="'testAction'" model="'test'" limit="10" nullText="'Remote'"/>`;
        }
    );
    const { getEditableContent } = await setupHTMLBuilder(`
        <div class="test-options-target">b</div>
    `);
    const editableContent = getEditableContent();
    await contains(":iframe .test-options-target").click();
    await contains(".btn.o-dropdown").click();
    await contains("span.o-dropdown-item:contains('Remote')").click();
    expect(editableContent.textContent.trim()).toBe("Remote");
    await contains(".btn.o-dropdown").click();
    await contains("span.o-dropdown-item:contains('First')").click();
    expect(editableContent.textContent.trim()).toBe("First");
});
