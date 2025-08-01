import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    addOption,
    addPlugin,
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "./website_helpers";
import { Plugin } from "@html_editor/plugin";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { setSelection } from "@html_editor/../tests/_helpers/selection";

defineWebsiteModels();

test("Check contenteditable attribute", async () => {
    expect.assertions(8);

    await setupWebsiteBuilder(`
        <section>
            <div class="not_a_container_class">
                <div class="container"></div>
            </div>
        </section>
        <section><div class="o_container_small"></div></section>
        <section><div class="container-fluid"></div></section>
        <section>
            <div class="container">
                <div class="o_we_bg_filter"></div>
                <div class="o_we_shape"></div>
            </div>
        </section>
    `);
    expect(":iframe section:not([contenteditable=false]) > .not_a_container_class").toHaveCount(1);
    expect(
        ":iframe section[contenteditable=false] > .o_container_small[contenteditable=true]"
    ).toHaveCount(1);
    expect(
        ":iframe section[contenteditable=false] > .container-fluid[contenteditable=true]"
    ).toHaveCount(1);
    expect(":iframe section[contenteditable=false] > .container[contenteditable=true]").toHaveCount(
        1
    );
    expect(":iframe .o_we_bg_filter[contenteditable=false]").toHaveCount(1);
    expect(":iframe .o_we_shape[contenteditable=false]").toHaveCount(1);

    onRpc("ir.ui.view", "save", ({ args }) => {
        // Make sure the content is saved and doesn't contain "contenteditable"
        expect(args[1].includes("<section")).toBe(true);
        expect(args[1].includes("contenteditable")).toBe(false);
        return true;
    });
    queryOne(":iframe .o_container_small").textContent = "dirty for save";
    await contains(".o-snippets-top-actions [data-action='save']").click();
});

test("Check contenteditable on Parallax snippet", async () => {
    await setupWebsiteBuilderWithSnippet("s_parallax");
    expect(":iframe section.s_parallax > .oe_structure[contenteditable=false]").toHaveCount(1);
});

test("Do not set contenteditable attribute on data-oe-readonly", async () => {
    class TestPlugin extends Plugin {
        static id = "testPlugin";
        resources = {
            force_editable_selector: ".target",
            force_not_editable_selector: ".non-editable",
        };
    }
    addPlugin(TestPlugin);
    addOption({
        selector: ".target",
        template: xml`<BuilderButton classAction="'test-class'">Test</BuilderButton>`,
    });
    await setupWebsiteBuilder(`
        <section>
            <div class="non-editable">
                <div class="target" data-oe-model="test" data-oe-field="test" data-oe-id="1" data-oe-readonly="true">
                    test
                </div>
            </div>
        </section>
    `);
    expect(":iframe .target").not.toHaveAttribute("contenteditable");
    await contains(":iframe .target").click();
    await contains(".options-container [data-class-action='test-class']").click();
    expect(":iframe .target").not.toHaveAttribute("contenteditable");
});

test("Set contenteditable to false on elements that have the o_not_editable class", async () => {
    await setupWebsiteBuilder(`
        <section>
            <div class="target o_not_editable" data-oe-model="test" data-oe-field="test" data-oe-id="1">
                test
            </div>
        </section>
    `);
    expect(":iframe .target").toHaveAttribute("contenteditable", "false");
});

test("Set contenteditable to false on empty arch field", async () => {
    await setupWebsiteBuilder("");
    expect(":iframe #wrap").toHaveAttribute("contenteditable", "false");
});

test("feff on links are cleaned up", async () => {
    onRpc("ir.ui.view", "save", ({ args }) => {
        // Check that the saved content has no feff
        expect(args[1]).toBe(
            `<div id="wrap" class="oe_structure oe_empty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"><section class="o_colored_level"><a href="http://test.test">texst</a></section></div>`
        );
        expect.step("save");
        return true;
    });
    const { getEditor } = await setupWebsiteBuilder(
        `<section><a href="http://test.test">test</a></section>`
    );
    const link = queryOne(":iframe a");
    setSelection({ anchorNode: link.childNodes[1], anchorOffset: 2 });
    await insertText(getEditor(), "x");
    expect(link.innerText).toMatch(/\u{FEFF}/u);
    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect.verifySteps(["save"]);
});
