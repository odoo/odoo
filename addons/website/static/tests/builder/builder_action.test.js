import { xml } from "@odoo/owl";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    advanceTime,
    animationFrame,
    click,
    Deferred,
    press,
    queryOne,
    waitFor,
} from "@odoo/hoot-dom";
import { Plugin } from "@html_editor/plugin";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { expandToolbar } from "@html_editor/../tests/_helpers/toolbar";
import {
    addBuilderAction,
    addBuilderOption,
    waitForEndOfOperation,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import {
    contains,
    defineModels,
    fields,
    models,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { addPlugin, defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { WebsiteBuilderClientAction } from "@website/client_actions/website_preview/website_builder_action";

beforeEach(defineWebsiteModels);

test("trigger mobile view", async () => {
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    expect(".o_website_preview.o_is_mobile").toHaveCount(0);
    await contains("button[data-action='mobile']").click();
    expect(".o_website_preview.o_is_mobile").toHaveCount(1);
});

test("top window url in action context parameter", async () => {
    let websiteBuilder;
    patchWithCleanup(WebsiteBuilderClientAction.prototype, {
        setup() {
            websiteBuilder = this;
            this.props.action.context = {
                params: {
                    path: "/web/content/",
                },
            };
            super.setup();
        },
    });
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    expect(websiteBuilder.initialUrl).toBe("/website/force/1?path=%2F");
});

test("getRecordInfo retrieves the info from the #wrap element", async () => {
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            user_commands: [
                {
                    id: "test_cmd",
                    run: () => {
                        const recordInfo = this.config.getRecordInfo();
                        expect.step(`getRecordInfo ${JSON.stringify(recordInfo)}`);
                    },
                },
            ],
            toolbar_groups: { id: "test_group" },
            toolbar_items: [
                {
                    id: "test_btn",
                    groupId: "test_group",
                    commandId: "test_cmd",
                    description: "Test Button",
                },
            ],
        };
    }
    addPlugin(TestPlugin);

    const { getEditor } = await setupWebsiteBuilder(`<p>plop</p>`);
    const editor = getEditor();
    const p = editor.editable.querySelector("p");
    setSelection({
        anchorNode: p.firstChild,
        anchorOffset: 0,
        focusOffset: 4,
    });

    await waitFor(".o-we-toolbar");
    await expandToolbar();
    await click(".o-we-toolbar .btn[name=test_btn]");

    expect.verifySteps(['getRecordInfo {"resModel":"ir.ui.view","resId":"539","field":"arch"}']);
});

test("elements within iframe can't be clicked while the builder is being set up", async () => {
    const def = new Deferred();
    patchWithCleanup(WebsiteBuilderClientAction.prototype, {
        async loadIframeAndBundles(isEditing) {
            super.loadIframeAndBundles(isEditing);
            await def;
        },
    });
    await setupWebsiteBuilder(
        `<section class="test-section"><button onclick="window.step()">Click me</button></section>`,
        { openEditor: false }
    );
    const iframeEl = queryOne("iframe");
    iframeEl.contentWindow.step = () => expect.step("button clicked");
    await contains(":iframe .test-section button").click();
    expect.verifySteps(["button clicked"]);
    // Reimplementation of openBuilderSidebar().
    await click(".o-website-btn-custo-primary");
    // The button should not be clickable.
    await expect(click(":iframe .test-section button")).rejects.toThrow(
        `found 0 elements instead of 1: 1 matching ":iframe .test-section button" (1 iframe element), including 0 interactive elements`
    );
    expect.verifySteps([]);
    def.resolve();
    await advanceTime(200);
    await contains(":iframe .test-section button").click();
    await animationFrame();
    expect.verifySteps(["button clicked"]);
});

describe.tags("desktop");
describe("BuilderMany2One: exit editor when previewing", () => {
    beforeEach(async () => {
        class Test extends models.Model {
            _name = "test";
            _records = [
                { id: 1, name: "First" },
                { id: 2, name: "Second" },
                { id: 3, name: "Third" },
            ];
            name = fields.Char();
        }
        onRpc("test", "name_search", () => [
            [1, "First"],
            [2, "Second"],
            [3, "Third"],
        ]);

        defineModels([Test]);

        addBuilderAction({
            testAction: class extends BuilderAction {
                static id = "testAction";
                apply({ editingElement, value }) {
                    editingElement.textContent = JSON.parse(value).name;
                    editingElement.dataset.test = value;
                }
                getValue({ editingElement }) {
                    return editingElement.dataset.test;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderMany2One action="'testAction'" model="'test'" limit="10" preview="true"/>`;
            }
        );

        await setupWebsiteBuilder(`<div class="test-options-target">Homepage</div>`);
        await contains(":iframe .test-options-target").click();
        await contains(".btn.o-dropdown").click();
        await waitFor(".o-dropdown-item:contains(First)");
        await animationFrame();
        expect(":iframe .test-options-target").toHaveText("First", {
            message: "It should preview the first element",
        });
    });

    test("save", async () => {
        await press(["alt", "s"]);
        await waitForEndOfOperation();
        expect(":iframe .test-options-target").toHaveText("Homepage", {
            message: "The preview should have been reverted",
        });
    });

    test("discard", async () => {
        await press(["alt", "j"]);
        await waitForEndOfOperation();
        expect(".o_dialog").toHaveCount(0, {
            message: "There should be no confirmation dialog since we didn't modify anything",
        });
        expect(":iframe .test-options-target").toHaveText("Homepage", {
            message: "The preview should have been reverted",
        });
    });
});
