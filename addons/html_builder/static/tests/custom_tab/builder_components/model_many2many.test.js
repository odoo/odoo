import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
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
class TestBase extends models.Model {
    _name = "test.base";
    _records = [
        {
            id: 1,
            rel: [],
        },
    ];
    rel = fields.Many2many({
        relation: "test",
        string: "Test",
    });
}

describe.current.tags("desktop");
defineModels([Test, TestBase]);

test("model many2many: find tag, select tag, unselect tag", async () => {
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
            static template = xml`<ModelMany2Many baseModel="'test.base'" m2oField="'rel'" recordId="1"/>`;
        }
    );
    const { getEditor } = await setupHTMLBuilder(
        `<div class="test-options-target" data-res-model="test.base" data-res-id="1">b</div>`
    );

    await contains(":iframe .test-options-target").click();
    const modelEdit = getEditor().shared.cachedModel.useModelEdit({
        model: "test.base",
        recordId: 1,
    });
    expect(".options-container").toBeDisplayed();
    expect("table tr").toHaveCount(0);
    expect(modelEdit.get("rel")).toEqual([]);

    await contains(".btn.o-dropdown").click();
    expect("input").toHaveCount(1);
    await contains("input").click();
    await delay(300); // debounce
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(3);
    await contains("span.o-dropdown-item").click();
    expect(modelEdit.get("rel")).toEqual([{ id: 1, name: "First", display_name: "First" }]);
    expect("table tr").toHaveCount(1);

    await contains(".btn.o-dropdown").click();
    await delay(300); // debounce
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(2);
    await contains("span.o-dropdown-item").click();
    expect(modelEdit.get("rel")).toEqual([
        { id: 1, name: "First", display_name: "First" },
        { id: 2, name: "Second", display_name: "Second" },
    ]);
    expect("table tr").toHaveCount(2);

    await contains("button.fa-minus").click();
    expect(modelEdit.get("rel")).toEqual([{ id: 2, name: "Second", display_name: "Second" }]);
    expect("table tr").toHaveCount(1);
    expect("table input").toHaveValue("Second");

    await contains(".o-snippets-tabs button").click();
    await contains(":iframe .test-options-target").click();
    expect("table tr").toHaveCount(1);
    expect("table input").toHaveValue("Second");
    expect.verifySteps(["name_search", "name_search"]);
});
