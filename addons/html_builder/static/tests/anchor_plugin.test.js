import {
    addBuilderOption,
    addBuilderPlugin,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { Plugin } from "@html_editor/plugin";
import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

test("Should show anchor button based on resource selectors", async () => {
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            anchor_allowed_selectors: ".allowed1 *, .allowed2",
            anchor_excluded_selectors: ".excluded",
        };
    }

    addBuilderPlugin(TestPlugin);
    addBuilderOption({
        selector: ".allowed1, .allowed2, .excluded",
        template: xml`<BuilderButton classAction="'test'">Test</BuilderButton>`,
    });
    await setupHTMLBuilder(`
            <div data-name="Link creation allowed1" class="allowed1">
                Allowed link to be created
                <div data-name="Link creation not allowed" class="excluded">
                    Not allowed link to be created
                    <div data-name="Link creation allowed2" class="allowed2">
                        Allowed link to be created
                    </div>
                </div>
            </div>
        `);

    await contains(":iframe .allowed2").click();
    expect("[data-container-title='Link creation allowed1'] .oe_snippet_anchor").toHaveCount(1);
    expect("[data-container-title='Link creation not allowed'] .oe_snippet_anchor").toHaveCount(0);
    expect("[data-container-title='Link creation allowed2'] .oe_snippet_anchor").toHaveCount(1);
});
