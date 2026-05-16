import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { xml } from "@odoo/owl";
import { contains, defineModels, fields, models, onRpc } from "@web/../tests/web_test_helpers";
import { delay } from "@web/core/utils/concurrency";
import { BaseOptionComponent } from "@html_builder/core/utils";

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

test("many2many: find tag, select tag, unselect tag", async () => {
    let executeCount = 0;
    onRpc("test", "name_search", ({ kwargs }) => {
        expect.step("name_search");
        executeCount++;
        if (executeCount === 1) {
            expect(kwargs.domain).toEqual([]);
        }
        if (executeCount === 2) {
            expect(kwargs.domain).toEqual([["id", "not in", [1]]]);
        }
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderMany2Many dataAttributeAction="'test'" model="'test'" limit="10"/>`;
        }
    );
    const { getEditableContent } = await setupHTMLBuilder(
        `<div class="test-options-target">b</div>`
    );
    const editableContent = getEditableContent();

    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect("table tr").toHaveCount(0);
    expect(editableContent).toHaveInnerHTML(`<div class="test-options-target">b</div>`);

    await contains(".btn.o-dropdown").click();
    expect("input").toHaveCount(1);
    await contains("input").click();
    await delay(300); // debounce
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(3);
    await contains("span.o-dropdown-item").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="test-options-target" data-test="[{&quot;id&quot;:1,&quot;display_name&quot;:&quot;First&quot;,&quot;name&quot;:&quot;First&quot;}]">b</div>`
    );
    expect("table tr").toHaveCount(1);

    await contains(".btn.o-dropdown").click();
    await delay(300); // debounce
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(2);
    await contains("span.o-dropdown-item").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="test-options-target" data-test="[{&quot;id&quot;:1,&quot;display_name&quot;:&quot;First&quot;,&quot;name&quot;:&quot;First&quot;},{&quot;id&quot;:2,&quot;display_name&quot;:&quot;Second&quot;,&quot;name&quot;:&quot;Second&quot;}]">b</div>`
    );
    expect("table tr").toHaveCount(2);

    await contains("button.fa-minus").click();
    expect.verifySteps(["name_search", "name_search"]);
    expect(editableContent).toHaveInnerHTML(
        `<div class="test-options-target" data-test="[{&quot;id&quot;:2,&quot;display_name&quot;:&quot;Second&quot;,&quot;name&quot;:&quot;Second&quot;}]">b</div>`
    );
    expect("table tr").toHaveCount(1);
    expect("table input").toHaveValue("Second");
});

test("many2many: async load", async () => {
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
            static template = xml`<BuilderMany2Many action="'testAction'" model="'test'" limit="10"/>`;
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
        `<div class="test-options-target" data-test="[{&quot;id&quot;:1,&quot;display_name&quot;:&quot;First&quot;,&quot;name&quot;:&quot;First&quot;}]">b</div>`
    );
});
