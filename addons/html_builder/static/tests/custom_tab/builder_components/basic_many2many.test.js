import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, reactive, xml } from "@odoo/owl";
import { delay } from "@web/core/utils/concurrency";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../website_helpers";
import { useBuilderComponents } from "@html_builder/core/utils";

defineWebsiteModels();

test.tags("focus required")("basic many2many: find tag, select tag, unselect tag", async () => {
    onRpc("/web/dataset/call_kw/test/name_search", async (args) => [
        [1, "First"],
        [2, "Second"],
        [3, "Third"],
    ]);
    class TestComponent extends Component {
        static template = xml`<BasicMany2Many selection="props.selection" model="'test'" setSelection="props.setSelection.bind(this)"/>`;
        static props = {
            selection: Array,
            setSelection: Function,
        };
        setup() {
            useBuilderComponents();
        }
    }
    const selection = reactive([]);
    addOption({
        selector: ".test-options-target",
        Component: TestComponent,
        props: {
            selection: selection,
            setSelection(newSelection) {
                selection.length = 0;
                for (const item of newSelection) {
                    selection.push(item);
                }
            },
        },
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);

    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect("table tr").toHaveCount(0);
    expect(selection).toEqual([]);

    await contains(".btn.o-dropdown").click();
    expect("input").toHaveCount(1);
    await contains("input").click();
    await delay(300); // debounce
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(3);
    await contains("span.o-dropdown-item").click();
    expect(selection).toEqual([{ id: 1, name: "First" }]);
    expect("table tr").toHaveCount(1);

    await contains(".btn.o-dropdown").click();
    await contains("input[placeholder]").click();
    await delay(300); // debounce
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(2);
    await contains("span.o-dropdown-item").click();
    expect(selection).toEqual([
        { id: 1, name: "First" },
        { id: 2, name: "Second" },
    ]);
    expect("table tr").toHaveCount(2);

    await contains("button.fa-minus").click();
    expect(selection).toEqual([{ id: 2, name: "Second" }]);
    expect("table tr").toHaveCount(1);
    expect("table input").toHaveValue("Second");
});
