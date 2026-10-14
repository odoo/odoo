import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { SnippetModel } from "@html_builder/snippets/snippet_service";
import { describe, expect, queryFirst, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");

// A theme color changed (e.g. by a website's palette): the shapes using it
// follow.
function addThemeColorOption() {
    addBuilderAction({
        ThemeColorAction: class extends BuilderAction {
            static id = "themeColor";
            apply() {
                for (const handler of this.getResource("on_website_color_updated_handlers")) {
                    handler(["o-color-5"]);
                }
            }
        },
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'themeColor'">Theme color</BuilderButton>`,
    });
}

const SHAPE_DATA = `{"shape":"html_builder/Connections/01","colors":{"c5":"o-color-5"}}`;

test("a theme color previewed refreshes the page's shapes, not the custom snippets", async () => {
    patch(SnippetModel.prototype, {
        async updateContent(category) {
            expect.step(`update ${category}`);
        },
    });
    addThemeColorOption();
    await setupHTMLBuilder(`
        <div class="test-options-target">Target</div>
        <section data-oe-shape-data='${SHAPE_DATA}'>
            <div class="o_we_shape" style="background-image: url('old.svg');"></div>
        </section>`);
    await contains(":iframe .test-options-target").click();
    await contains("[data-action-id='themeColor']").hover();
    expect(queryFirst(":iframe .o_we_shape").style.backgroundImage).not.toInclude("old.svg");
    expect.verifySteps([]);
    await contains("[data-action-id='themeColor']").click();
    // The background shapes' handler, then the image shapes'.
    expect.verifySteps(["update snippet_custom", "update snippet_custom"]);
});

test("a theme color only refreshes the shapes of the sections using it", async () => {
    addThemeColorOption();
    await setupHTMLBuilder(`
        <div class="test-options-target">Target</div>
        <section data-oe-shape-data='${SHAPE_DATA}'>
            <section class="test-inner">
                <div class="o_we_shape" style="background-image: url('inner.svg');"></div>
            </section>
        </section>`);
    await contains(":iframe .test-options-target").click();
    await contains("[data-action-id='themeColor']").click();
    expect(queryFirst(":iframe .test-inner .o_we_shape").style.backgroundImage).toInclude(
        "inner.svg"
    );
});
