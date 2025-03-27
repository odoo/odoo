import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { xml } from "@odoo/owl";
import { delay } from "@web/core/utils/concurrency";
import { contains, defineModels, fields, models, onRpc } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../website_helpers";

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

defineWebsiteModels();
defineModels([Test, TestBase]);

test("model many2many: find tag, select tag, unselect tag", async () => {
    onRpc("test", "name_search", () => [
        [1, "First"],
        [2, "Second"],
        [3, "Third"],
    ]);
    addOption({
        selector: ".test-options-target",
        template: xml`<ModelMany2Many baseModel="'test.base'" m2oField="'rel'" recordId="1"/>`,
    });
    const { getEditor } = await setupWebsiteBuilder(
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
});
