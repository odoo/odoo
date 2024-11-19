import { setContent } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { describe, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    fill,
    hover,
    queryAllTexts,
    queryFirst,
    queryOne,
} from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    openSnippetsMenu,
    patchToolboxesWithCleanup,
    setupWebsiteBuilder,
    getEditable,
} from "./helpers";

defineWebsiteModels();

test("open SnippetsMenu and discard", async () => {
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
    await openSnippetsMenu();
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(0);
    await click(".o-snippets-top-actions button:contains(Discard)");
    await animationFrame();
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
});

test("navigate between builder tab don't fetch snippet description again", async () => {
    onRpc("render_public_asset", () => {
        expect.step("render_public_asset");
    });
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    await openSnippetsMenu();
    expect(queryAllTexts(".o-website-snippetsmenu .o-snippets-tabs span")).toEqual([
        "BLOCKS",
        "CUSTOMIZE",
        "THEME",
    ]);
    expect(queryOne(".o-website-snippetsmenu .o-snippets-tabs span.active")).toHaveText("BLOCKS");
    expect.verifySteps(["render_public_asset"]);

    await contains(".o-website-snippetsmenu .o-snippets-tabs span:contains(THEME)").click();
    expect(queryOne(".o-website-snippetsmenu .o-snippets-tabs span.active")).toHaveText("THEME");

    await contains(".o-website-snippetsmenu .o-snippets-tabs span:contains(BLOCK)").click();
    expect(queryOne(".o-website-snippetsmenu .o-snippets-tabs span.active")).toHaveText("BLOCKS");
    expect.verifySteps([]);
});

test("undo and redo buttons", async () => {
    const { getEditor } = await setupWebsiteBuilder(getEditable("<p> Text </p>"));
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
    await openSnippetsMenu();
    expect(":iframe #wrap").not.toHaveClass("o_dirty");
    expect(":iframe #wrap").toHaveClass("o_editable");
    const editor = getEditor();
    setContent(
        editor.editable,
        getEditable(
            '<div id="wrap" class="o_editable" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"><p> Text[] </p></div>'
        )
    );
    await insertText(editor, "a");
    expect(editor.editable).toHaveInnerHTML(
        '<div id="wrap" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"> <div id="wrap" class="o_editable o_dirty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"> <p> Texta </p> </div> </div>'
    );
    await animationFrame();
    await click(".o-snippets-menu button.fa-undo");
    await animationFrame();
    expect(editor.editable).toHaveInnerHTML(
        '<div id="wrap" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch" class="o_editable"> <p> Text </p> </div>'
    );
    await click(".o-snippets-menu button.fa-repeat");
    expect(editor.editable).toHaveInnerHTML(
        '<div id="wrap" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"> <div id="wrap" class="o_editable o_dirty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"> <p> Texta </p> </div> </div>'
    );
});

test("Open toolbox", async () => {
    patchToolboxesWithCleanup({
        selector: ".test-toolbox-target",
        template: xml`
            <ElementToolboxContainer title="'TestToolbox'">
                Test toolbox
            </ElementToolboxContainer>`,
    });
    await setupWebsiteBuilder(`<div class="test-toolbox-target">b</div>`);
    await openSnippetsMenu();
    await click(":iframe .test-toolbox-target");
    await animationFrame();
    expect(".element-toolbox").toBeDisplayed();
});
describe("Web editor widgets", () => {
    describe("WeButton", () => {
        test("call a specific action with some params and value", async () => {
            patchToolboxesWithCleanup({
                selector: ".test-toolbox-target",
                actions: {
                    customAction: {
                        apply: ({ param, value }) => {
                            expect.step(`customAction ${param} ${value}`);
                        },
                    },
                },
                template: xml`
                    <ElementToolboxContainer title="'TestToolbox'">
                        <WeButton action="'customAction'" actionParam="'myParam'" actionValue="'myValue'">MyAction</WeButton>
                    </ElementToolboxContainer>`,
            });
            await setupWebsiteBuilder(`<div class="test-toolbox-target">b</div>`);
            await openSnippetsMenu();
            await click(":iframe .test-toolbox-target");
            await animationFrame();
            expect(".element-toolbox").toBeDisplayed();
            expect("[data-action-id='customAction']").toHaveText("MyAction");
            await click("[data-action-id='customAction']");
            // The function `apply` should be called twice (on hover (for preview), then, on click).
            expect.verifySteps(["customAction myParam myValue", "customAction myParam myValue"]);
        });
        test("call a shorthand action", async () => {
            patchToolboxesWithCleanup({
                selector: ".test-toolbox-target",
                template: xml`
                    <ElementToolboxContainer title="'TestToolbox'">
                        <WeButton classAction="'my-custom-class'"/>
                    </ElementToolboxContainer>`,
            });
            await setupWebsiteBuilder(`<div class="test-toolbox-target">b</div>`);
            await openSnippetsMenu();
            await click(":iframe .test-toolbox-target");
            await animationFrame();
            expect(".element-toolbox").toBeDisplayed();
            await click("[data-class-action='my-custom-class']");
            expect(":iframe .test-toolbox-target").toHaveClass("my-custom-class");
        });
        test("call a shorthand action and a specific action", async () => {
            patchToolboxesWithCleanup({
                selector: ".test-toolbox-target",
                actions: {
                    customAction: {
                        apply: ({ editingElement }) => {
                            expect.step(`customAction`);
                            editingElement.innerHTML = "c";
                        },
                    },
                },
                template: xml`
                    <ElementToolboxContainer title="'TestToolbox'">
                        <WeButton action="'customAction'" classAction="'my-custom-class'"/>
                    </ElementToolboxContainer>`,
            });
            await setupWebsiteBuilder(`<div class="test-toolbox-target">b</div>`);
            await openSnippetsMenu();
            await click(":iframe .test-toolbox-target");
            await animationFrame();
            expect(".element-toolbox").toBeDisplayed();
            await click("[data-action-id='customAction'][data-class-action='my-custom-class']");
            expect(":iframe .test-toolbox-target").toHaveClass("my-custom-class");
            // The function `apply` should be called twice (on hover (for preview), then, on click).
            expect.verifySteps(["customAction", "customAction"]);
            expect(":iframe .test-toolbox-target").toHaveInnerHTML("c");
        });
        test("preview a shorthand action and a specific action", async () => {
            patchToolboxesWithCleanup({
                selector: ".test-toolbox-target",
                actions: {
                    customAction: {
                        apply: ({ editingElement }) => {
                            expect.step(`customAction`);
                            editingElement.innerHTML = "c";
                        },
                    },
                },
                template: xml`
                    <ElementToolboxContainer title="'TestToolbox'">
                        <WeButton action="'customAction'" classAction="'my-custom-class'"/>
                    </ElementToolboxContainer>`,
            });
            await setupWebsiteBuilder(`<div class="test-toolbox-target">b</div>`);
            await openSnippetsMenu();
            await click(":iframe .test-toolbox-target");
            await animationFrame();
            expect(".element-toolbox").toBeDisplayed();
            await hover("[data-action-id='customAction'][data-class-action='my-custom-class']");
            expect(":iframe .test-toolbox-target").toHaveClass("my-custom-class");
            expect.verifySteps(["customAction"]);
            expect(":iframe .test-toolbox-target").toHaveInnerHTML("c");
            await hover(".test-toolbox-target");
            expect(":iframe .test-toolbox-target").toHaveInnerHTML("b");
            expect.verifySteps([]);
        });
        test("clean another action", async () => {
            patchToolboxesWithCleanup({
                selector: ".test-toolbox-target",
                template: xml`
                    <ElementToolboxContainer title="'TestToolbox'">
                        <WeButtonGroup>
                            <WeButton classAction="'my-custom-class1'"/>
                            <WeButton classAction="'my-custom-class2'"/>
                        </WeButtonGroup>
                    </ElementToolboxContainer>`,
            });
            await setupWebsiteBuilder(`<div class="test-toolbox-target">b</div>`);
            await openSnippetsMenu();
            await click(":iframe .test-toolbox-target");
            await animationFrame();
            expect(".element-toolbox").toBeDisplayed();
            await click("[data-class-action='my-custom-class1']");
            expect(":iframe .test-toolbox-target").toHaveAttribute(
                "class",
                "test-toolbox-target my-custom-class1"
            );
            await click("[data-class-action='my-custom-class2']");
            expect(":iframe .test-toolbox-target").toHaveAttribute(
                "class",
                "test-toolbox-target my-custom-class2"
            );
        });
        test("add the active class if the condition is met", async () => {
            patchToolboxesWithCleanup({
                selector: ".test-toolbox-target",
                template: xml`
                    <ElementToolboxContainer title="'TestToolbox'">
                        <WeButton classAction="'my-custom-class1'"/>
                        <WeButton classAction="'my-custom-class2'"/>
                    </ElementToolboxContainer>`,
            });
            await setupWebsiteBuilder(`<div class="test-toolbox-target my-custom-class1">b</div>`);
            await openSnippetsMenu();
            await click(":iframe .test-toolbox-target");
            await animationFrame();
            expect("[data-class-action='my-custom-class1']").toHaveClass("active");
            expect("[data-class-action='my-custom-class2']").not.toHaveClass("active");
        });
    });
    describe("WeButtonGroup", () => {
        test("change the editingElement of sub widget through `applyTo` prop", async () => {
            patchToolboxesWithCleanup({
                selector: ".test-toolbox-target",
                actions: {
                    customAction: {
                        apply: ({ editingElement }) => {
                            expect.step(`customAction ${editingElement.className}`);
                        },
                    },
                },
                template: xml`
                    <ElementToolboxContainer title="'TestToolbox'">
                        <WeButtonGroup applyTo="'.a'">
                            <WeButton action="'customAction'"/>
                        </WeButtonGroup>
                    </ElementToolboxContainer>`,
            });
            await setupWebsiteBuilder(`
                <div class="test-toolbox-target">
                    <div class="a">b</div>
                </div>
            `);
            await openSnippetsMenu();
            await click(":iframe .test-toolbox-target");
            await animationFrame();
            expect(".element-toolbox").toBeDisplayed();
            await hover("[data-action-id='customAction']");
            expect.verifySteps(["customAction a"]);
        });
        test("should propagate actionParam in the context", async () => {
            patchToolboxesWithCleanup({
                selector: ".test-toolbox-target",
                actions: {
                    customAction: {
                        apply: ({ param }) => {
                            expect.step(`customAction ${param}`);
                        },
                    },
                },
                template: xml`
                    <ElementToolboxContainer title="'TestToolbox'">
                        <WeButtonGroup actionParam="'myParam'">
                            <WeButton action="'customAction'"/>
                        </WeButtonGroup>
                    </ElementToolboxContainer>`,
            });
            await setupWebsiteBuilder(`
                <div class="test-toolbox-target">
                    <div class="a">b</div>
                </div>
            `);
            await openSnippetsMenu();
            await click(":iframe .test-toolbox-target");
            await animationFrame();
            expect(".element-toolbox").toBeDisplayed();
            await hover("[data-action-id='customAction']");
            expect.verifySteps(["customAction myParam"]);
        });
    });
    describe("WeNumberInput", () => {
        test("should get the initial value of the input", async () => {
            patchToolboxesWithCleanup({
                selector: ".test-toolbox-target",
                actions: {
                    customAction: {
                        getValue: ({ editingElement }) => {
                            return editingElement.innerHTML;
                        },
                        apply: ({ param }) => {
                            expect.step(`customAction ${param}`);
                        },
                    },
                },
                template: xml`
                    <ElementToolboxContainer title="'TestToolbox'">
                        <WeNumberInput action="'customAction'"/>
                    </ElementToolboxContainer>`,
            });
            await setupWebsiteBuilder(`
                <div class="test-toolbox-target">10</div>
            `);
            await openSnippetsMenu();
            await click(":iframe .test-toolbox-target");
            await animationFrame();
            expect(".element-toolbox").toBeDisplayed();
            const input = queryFirst(".element-toolbox input");
            expect(input).toHaveValue("10");
        });
        test("should preview changes", async () => {
            patchToolboxesWithCleanup({
                selector: ".test-toolbox-target",
                actions: {
                    customAction: {
                        getValue: ({ editingElement }) => {
                            return editingElement.innerHTML;
                        },
                        apply: ({ editingElement, value }) => {
                            expect.step(`customAction ${value}`);
                            editingElement.innerHTML = value;
                        },
                    },
                },
                template: xml`
                    <ElementToolboxContainer title="'TestToolbox'">
                        <WeNumberInput action="'customAction'"/>
                    </ElementToolboxContainer>`,
            });
            await setupWebsiteBuilder(`
                <div class="test-toolbox-target">10</div>
            `);
            await openSnippetsMenu();
            await click(":iframe .test-toolbox-target");
            await animationFrame();
            expect(".element-toolbox").toBeDisplayed();
            await click(".element-toolbox input");
            await fill("2");
            expect.verifySteps(["customAction 102"]);
            expect(":iframe .test-toolbox-target").toHaveInnerHTML("102");
            expect(".o-snippets-top-actions .fa-undo").not.toBeEnabled();
            expect(".o-snippets-top-actions .fa-repeat").not.toBeEnabled();
        });
        test("should commit changes", async () => {
            patchToolboxesWithCleanup({
                selector: ".test-toolbox-target",
                actions: {
                    customAction: {
                        getValue: ({ editingElement }) => {
                            return editingElement.innerHTML;
                        },
                        apply: ({ editingElement, value }) => {
                            expect.step(`customAction ${value}`);
                            editingElement.innerHTML = value;
                        },
                    },
                },
                template: xml`
                    <ElementToolboxContainer title="'TestToolbox'">
                        <WeNumberInput action="'customAction'"/>
                    </ElementToolboxContainer>`,
            });
            await setupWebsiteBuilder(`
                <div class="test-toolbox-target">10</div>
            `);
            await openSnippetsMenu();
            await click(":iframe .test-toolbox-target");
            await animationFrame();
            expect(".element-toolbox").toBeDisplayed();
            await click(".element-toolbox input");
            await fill("2");
            expect.verifySteps(["customAction 102"]);
            expect(":iframe .test-toolbox-target").toHaveInnerHTML("102");
            await click(document.body);
            await animationFrame();
            expect.verifySteps(["customAction 102"]);
            expect(".o-snippets-top-actions .fa-undo").toBeEnabled();
            expect(".o-snippets-top-actions .fa-repeat").not.toBeEnabled();
        });
    });
    describe("WeSelectItem", () => {
        test("call a specific action with some params and value (WeSelectItem)", async () => {
            patchToolboxesWithCleanup({
                selector: ".test-toolbox-target",
                actions: {
                    customAction: {
                        apply: ({ param, value }) => {
                            expect.step(`customAction ${param} ${value}`);
                        },
                    },
                },
                template: xml`
                    <ElementToolboxContainer title="'TestToolbox'">
                        <WeSelect label="'MySelect'">
                            <WeSelectItem action="'customAction'" actionParam="'myParam'" actionValue="'myValue'">MyAction</WeSelectItem>
                        </WeSelect>
                    </ElementToolboxContainer>`,
            });
            await setupWebsiteBuilder(`<div class="test-toolbox-target">b</div>`);
            await openSnippetsMenu();
            await click(":iframe .test-toolbox-target");
            await animationFrame();
            expect(".element-toolbox").toBeDisplayed();
            await click(".we-bg-toolbox .dropdown");
            await animationFrame();
            expect("[data-action-id='customAction']").toHaveText("MyAction");
            await click("[data-action-id='customAction']");
            // The function `apply` should be called twice (on hover (for preview), then, on click).
            expect.verifySteps(["customAction myParam myValue", "customAction myParam myValue"]);
        });
    });
});
