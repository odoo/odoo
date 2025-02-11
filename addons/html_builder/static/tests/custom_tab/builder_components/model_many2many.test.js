import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, reactive, xml } from "@odoo/owl";
import { delay } from "@web/core/utils/concurrency";
import { contains, defineModels, fields, models, onRpc } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../helpers";
import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";

class Test extends models.Model {
    _name = "test";
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
    onRpc("/web/dataset/call_kw/test/name_search", async (args) => [
        [1, "First"],
        [2, "Second"],
        [3, "Third"],
    ]);
    class TestComponent extends Component {
        static template = xml`<ModelMany2Many baseModel="'test.base'" m2oField="'rel'" recordId="1" useModelEditState="props.useModelEditState"/>`;
        static props = {
            useModelEditState: Function,
        };
        static components = { ...defaultBuilderComponents };
    }
    const temporary = reactive({
        selection: undefined,
    });
    const useModelEditState = ({ model, recordId }) => temporary;
    addOption({
        selector: ".test-options-target",
        Component: TestComponent,
        props: {
            useModelEditState: useModelEditState,
        },
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);

    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect("table tr").toHaveCount(0);
    expect(temporary.selection).toEqual([]);

    await contains(".btn.o-dropdown").click();
    expect("input").toHaveCount(1);
    await contains("input").click();
    await delay(300); // debounce
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(3);
    await contains("span.o-dropdown-item").click();
    expect(temporary.selection).toEqual([{ id: 1, name: "First" }]);
    expect("table tr").toHaveCount(1);

    await contains(".btn.o-dropdown").click();
    await contains("input[placeholder]").click();
    await delay(300); // debounce
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(2);
    await contains("span.o-dropdown-item").click();
    expect(temporary.selection).toEqual([
        { id: 1, name: "First" },
        { id: 2, name: "Second" },
    ]);
    expect("table tr").toHaveCount(2);

    await contains("button.fa-minus").click();
    expect(temporary.selection).toEqual([{ id: 2, name: "Second" }]);
    expect("table tr").toHaveCount(1);
    expect("table input").toHaveValue("Second");

    await contains(".o-snippets-tabs button").click();
    await contains(".o-snippets-tabs button:nth-child(2)").click();
    expect("table tr").toHaveCount(1);
    expect("table input").toHaveValue("Second");
});
