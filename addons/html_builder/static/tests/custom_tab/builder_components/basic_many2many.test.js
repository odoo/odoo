import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { reactive, xml } from "@odoo/owl";
import { contains, defineModels, fields, models, onRpc } from "@web/../tests/web_test_helpers";
import { delay } from "@web/core/utils/concurrency";

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

test.tags("focus required");
test("basic many2many: find tag, select tag, unselect tag", async () => {
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
    const selection = reactive([]);
    class TestComponent extends BaseOptionComponent {
        static selector = ".test-options-target";
        static template = xml`<BasicMany2Many selection="this.selection" model="'test'" setSelection="this.setSelection.bind(this)"/>`;
        selection = selection;
        setSelection(newSelection) {
            selection.length = 0;
            for (const item of newSelection) {
                selection.push(item);
            }
        }
    }
    addBuilderOption(TestComponent);
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);

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
    expect(selection).toEqual([{ id: 1, name: "First", display_name: "First" }]);
    expect("table tr").toHaveCount(1);

    await contains(".btn.o-dropdown").click();
    await delay(300); // debounce
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(2);
    await contains("span.o-dropdown-item").click();
    expect(selection).toEqual([
        { id: 1, name: "First", display_name: "First" },
        { id: 2, name: "Second", display_name: "Second" },
    ]);
    expect("table tr").toHaveCount(2);

    await contains("button.fa-minus").click();
    expect(selection).toEqual([{ id: 2, name: "Second", display_name: "Second" }]);
    expect("table tr").toHaveCount(1);
    expect("table input").toHaveValue("Second");
    expect.verifySteps(["name_search", "name_search"]);
});

test("basic many2many: toggle dropdown without changing search term or selection does not trigger a new search", async () => {
    let executeCount = 0;
    onRpc("test", "name_search", ({ kwargs }) => {
        expect.step("name_search");
        executeCount++;
        if (executeCount === 1) {
            expect(kwargs.domain).toEqual([]);
        }
    });
    const selection = reactive([]);
    class TestComponent extends BaseOptionComponent {
        static selector = ".test-options-target";
        static template = xml`<BasicMany2Many selection="this.selection" model="'test'" setSelection="this.setSelection.bind(this)" limit="1"/>`;
        selection = selection;
        setSelection(newSelection) {
            selection.length = 0;
            for (const item of newSelection) {
                selection.push(item);
            }
        }
    }
    addBuilderOption(TestComponent);
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);

    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect("table tr").toHaveCount(0);
    expect(selection).toEqual([]);

    // Click to open, 1st search should be done
    await contains(".btn.o-dropdown").click();
    await delay(300); // debounce
    await animationFrame();
    expect(selection).toEqual([]);
    expect(executeCount).toBe(1);
    await contains(".btn.o-dropdown").click();

    // Toogle dropdown, no new search should be done
    await contains(".btn.o-dropdown").click();
    await delay(300); // debounce
    await animationFrame();
    expect(selection).toEqual([]);
    // Still same as no item is selected
    expect(executeCount).toBe(1);
    await contains(".btn.o-dropdown").click();
    await contains(".btn.o-dropdown").click();
    await delay(300); // debounce
    await animationFrame();
    expect(selection).toEqual([]);
    expect("span.o-dropdown-item").toHaveCount(1);
    await contains("span.o-dropdown-item").click();
    expect("table tr").toHaveCount(1);

    // Open again, now a second search should be done because selection changed
    await contains(".btn.o-dropdown").click();
    await delay(300); // debounce
    await animationFrame();
    expect("span.o-dropdown-item").toHaveCount(1);
    expect(selection).toEqual([{ id: 1, name: "First", display_name: "First" }]);
    expect(executeCount).toBe(2);
    expect.verifySteps(["name_search", "name_search"]);
});
