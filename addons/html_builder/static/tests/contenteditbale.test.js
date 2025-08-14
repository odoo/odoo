import { expect, test } from "@odoo/hoot";
import { addBuilderPlugin, setupHTMLBuilder } from "./helpers";
import { Plugin } from "@html_editor/plugin";

test("Do not set contenteditable to true on elements inside o_not_editable", async () => {
    class TestPlugin extends Plugin {
        static id = "testPlugin";
        resources = {
            force_editable_selector: ".target",
        };
    }
    addBuilderPlugin(TestPlugin);
    await setupHTMLBuilder(`
        <section>
            <div class="o_not_editable">
                <div class="target">
                    Hello
                </div>
            </div>
        </section>
    `);
    expect(":iframe .target").not.toHaveAttribute("contenteditable", "true");
});
