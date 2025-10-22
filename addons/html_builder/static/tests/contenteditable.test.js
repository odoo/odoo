import {
    addBuilderOption,
    addBuilderPlugin,
    setupHTMLBuilder,
    dummyBase64Img,
} from "@html_builder/../tests/helpers";
import { Plugin } from "@html_editor/plugin";
import { expect, test, describe } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

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

test("clone of editable media inside not editable area should be editable", async () => {
    onRpc("/html_editor/get_image_info", () => ({}));
    addBuilderOption({
        selector: "section",
        template: xml`<BuilderButton classAction="'test'">Test</BuilderButton>`,
    });
    addBuilderOption({
        selector: "img",
        template: xml`<BuilderButton classAction="'test'">Test Image</BuilderButton>`,
    });
    const { waitSidebarUpdated } = await setupHTMLBuilder(`
        <section>
            <div class="o_not_editable">
                <img class="o_editable_media" src="${dummyBase64Img}"/>
            </div>
        </section>
    `);
    await contains(":iframe img").click();
    await waitSidebarUpdated();
    expect(".options-container[data-container-title='Image']").toBeDisplayed();
    await contains(".oe_snippet_clone").click();
    await contains(":iframe section:last-of-type img").click();
    expect(".options-container[data-container-title='Image']").toBeDisplayed();
});
