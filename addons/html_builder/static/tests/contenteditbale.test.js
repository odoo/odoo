import { Plugin } from "@html_editor/plugin";
import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { addBuilderPlugin, setupHTMLBuilder } from "./helpers";

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

test("Media should not be replaceable if not inside a savable zone", async () => {
    await setupHTMLBuilder("", {
        headerContent: `
        <header id="top" data-anchor="true" data-name="Header">
            <i class="fa fa-shopping-cart fa-stack target" data-oe-model="ir.ui.view" data-oe-id="786" data-oe-field="arch" data-oe-xpath="/data/xpath/li[1]/a[1]"/>
        </header>`,
        styleContent: `
            .fa {
                display: flex;
                justify-content: center;
                align-items: center;
                width: 0.75rem;
                height: 0.75rem;
            }
        `,
    });
    expect(":iframe .target").toHaveClass("o_editable_media");
    await contains(":iframe #wrapwrap .target").click();
    expect("span:contains('Double-click to edit')").toHaveCount(0);
    await contains(":iframe #wrapwrap .target").dblclick();
    expect(".modal-content:contains(Select a media)").toHaveCount(0);
});
