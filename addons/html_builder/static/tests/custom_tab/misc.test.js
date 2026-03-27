import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { OptionsContainer } from "@html_builder/sidebar/option_container";
import { setContent, setSelection } from "@html_editor/../tests/_helpers/selection";
import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { withSequence } from "@html_editor/utils/resource";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import { onWillStart, xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("Open custom tab with template option", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
                <BuilderRow label="'Row 1'">
                    Test
                </BuilderRow>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target" data-name="Yop">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    expect(queryAllTexts(".options-container > div")).toEqual(["Yop", "Row 1\nTest"]);
});

test("Open custom tab with Component option", async () => {
    class TestOption extends BaseOptionComponent {
        static selector = ".test-options-target";
        static template = xml`
            <BuilderRow label="'Row 1'">
                Test
            </BuilderRow>`;
    }
    addBuilderOption(TestOption);
    await setupHTMLBuilder(`<div class="test-options-target" data-name="Yop">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    expect(queryAllTexts(".options-container > div")).toEqual(["Yop", "Row 1\nTest"]);
});

test("OptionContainer should display custom title", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
                <BuilderRow label="'Row 1'">
                    Test
                </BuilderRow>`;
            static title = "My custom title";
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target" data-name="Yop">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    expect(queryAllTexts(".options-container > div")).toEqual(["My custom title", "Row 1\nTest"]);
});

test("Don't display option base on exclude", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static exclude = ".test-exclude";
            static template = xml`<BuilderRow label="'Row 1'">a</BuilderRow>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static exclude = ".test-exclude-2";
            static template = xml`<BuilderRow label="'Row 2'">b</BuilderRow>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderRow label="'Row 3'">
                <BuilderButton classAction="'test-exclude-2'">c</BuilderButton>
            </BuilderRow>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target test-exclude">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(queryAllTexts(".options-container .hb-row")).toEqual(["Row 2\nb", "Row 3\nc"]);

    await contains("[data-class-action='test-exclude-2']").click();
    expect(queryAllTexts(".options-container .hb-row")).toEqual(["Row 3\nc"]);
});

test("Don't display option base on applyTo", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static applyTo = ".test-target";
            static template = xml`<BuilderRow label="'Row 1'">
                <BuilderButton classAction="'test-target-2'">a</BuilderButton>
            </BuilderRow>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static applyTo = ".test-target-2";
            static template = xml`<BuilderRow label="'Row 2'">b</BuilderRow>`;
        }
    );
    await setupHTMLBuilder(`
        <div class="test-options-target">
            <div class="test-target">b</div>
        </div>`);
    await contains(":iframe .test-options-target").click();
    expect(queryAllTexts(".options-container .hb-row")).toEqual(["Row 1\na"]);

    await contains("[data-class-action='test-target-2']").click();
    await animationFrame();
    expect(queryAllTexts(".options-container .hb-row")).toEqual(["Row 1\na", "Row 2\nb"]);
});

test("basic multi options containers", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
            <BuilderRow label="'Row 1'">A</BuilderRow>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".a";
            static template = xml`
            <BuilderRow label="'Row 2'">B</BuilderRow>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".main";
            static template = xml`
            <BuilderRow label="'Row 3'">C</BuilderRow>`;
        }
    );
    await setupHTMLBuilder(`<div class="main"><p class="test-options-target a">b</p></div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toHaveCount(2);
    expect(queryAllTexts(".options-container:first .we-bg-options-container > div > div")).toEqual([
        "Row 3",
        "C",
    ]);
    expect(
        queryAllTexts(".options-container:nth-child(2) .we-bg-options-container > div > div")
    ).toEqual(["Row 1", "A", "Row 2", "B"]);
});

test("option that matches several elements", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".a";
            static template = xml`<BuilderRow label="'Row'">
                <BuilderButton classAction="'my-custom-class'">Test</BuilderButton>
            </BuilderRow>`;
        }
    );

    await setupHTMLBuilder(`<div class="a"><div class="a test-target">b</div></div>`);
    await contains(":iframe .test-target").click();
    expect(".options-container:not(.d-none)").toHaveCount(2);
    expect(queryAllTexts(".options-container:not(.d-none)")).toEqual([
        "Block\nRow\nTest",
        "Block\nRow\nTest",
    ]);
});

test("Snippets options respect sequencing", async () => {
    addBuilderOption(
        withSequence(
            2,
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                <BuilderRow label="'Row 2'">
                    Test
                </BuilderRow>`;
            }
        )
    );
    addBuilderOption(
        withSequence(
            1,
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                <BuilderRow label="'Row 1'">
                    Test
                </BuilderRow>`;
            }
        )
    );
    addBuilderOption(
        withSequence(
            3,
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                <BuilderRow label="'Row 3'">
                    Test
                </BuilderRow>`;
            }
        )
    );
    await setupHTMLBuilder(`<div class="test-options-target" data-name="Yop">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeVisible();
    expect(queryAllTexts(".options-container .we-bg-options-container > div > div")).toEqual([
        "Row 1",
        "Test",
        "Row 2",
        "Test",
        "Row 3",
        "Test",
    ]);
});

test("hide empty OptionContainer and display OptionContainer with content", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderRow label="'Row 1'">
                <BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
            </BuilderRow>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target > div";
            static template = xml`<BuilderRow label="'Row 3'">
                <BuilderButton applyTo="'.my-custom-class'" classAction="'test'"/>
            </BuilderRow>`;
        }
    );
    await setupHTMLBuilder(
        `<div class="parent-target"><div><div class="child-target">b</div></div></div>`
    );

    await contains(":iframe .parent-target > div").click();
    expect(".options-container:not(.d-none)").toHaveCount(1);

    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container:not(.d-none)").toHaveCount(2);
});

test("hide empty OptionContainer and display OptionContainer with content (with BuilderButtonGroup)", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderRow label="'Row 1'">
                <BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
            </BuilderRow>`;
        }
    );

    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target > div";
            static template = xml`
                <BuilderRow label="'Row 2'">
                    <BuilderButtonGroup>
                        <BuilderButton applyTo="'.my-custom-class'" classAction="'test'">Test</BuilderButton>
                    </BuilderButtonGroup>
                </BuilderRow>`;
        }
    );

    await setupHTMLBuilder(
        `<div class="parent-target"><div><div class="child-target">b</div></div></div>`
    );
    await contains(":iframe .parent-target > div").click();
    expect(".options-container:not(.d-none)").toHaveCount(1);

    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container:not(.d-none)").toHaveCount(2);
    expect(".options-container:not(.d-none):nth-child(2)").toHaveText("Block\nRow 2\nTest");
});

test("hide empty OptionContainer and display OptionContainer with content (with BuilderButtonGroup) - 2", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderRow label="'Row 1'">
                <BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
            </BuilderRow>`;
        }
    );

    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target > div";
            static template = xml`
                <BuilderRow label="'Row 2'">
                    <BuilderButtonGroup applyTo="'.my-custom-class'">
                        <BuilderButton  classAction="'test'">Test</BuilderButton>
                    </BuilderButtonGroup>
                </BuilderRow>`;
        }
    );

    await setupHTMLBuilder(
        `<div class="parent-target"><div><div class="child-target">b</div></div></div>`
    );
    await contains(":iframe .parent-target > div").click();
    expect(".options-container:not(.d-none)").toHaveCount(1);

    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container:not(.d-none)").toHaveCount(2);
    expect(".options-container:not(.d-none):nth-child(2)").toHaveText("Block\nRow 2\nTest");
});

test("fallback on the 'Blocks' tab if no option match the selected element", async () => {
    await setupHTMLBuilder(`<div class="parent-target"><div class="child-target">b</div></div>`);
    await contains(":iframe .parent-target > div").click();
    expect(".o-snippets-tabs button:contains('Blocks')").toHaveClass("active");
});

test("display empty message if no option container is visible", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderRow label="'Row 1'">
                <BuilderButton applyTo="'.invalid'" classAction="'my-custom-class'"/>
            </BuilderRow>`;
        }
    );

    await setupHTMLBuilder(`<div class="parent-target"><div class="child-target">b</div></div>`);
    await contains(":iframe .parent-target > div").click();
    await animationFrame();
    expect(".o_customize_tab").toHaveText("Select a block on your page to style it.");
});
test("hide/display option base on selector", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderRow label="'Row 1'">
                <BuilderButton classAction="'my-custom-class'"/>
            </BuilderRow>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".my-custom-class";
            static template = xml`<BuilderRow label="'Row 2'">
                <BuilderButton classAction="'test'"/>
            </BuilderRow>`;
        }
    );

    await setupHTMLBuilder(`<div class="parent-target"><div class="child-target">b</div></div>`);
    await contains(":iframe .parent-target").click();
    expect("[data-class-action='test']").not.toHaveCount();

    await contains("[data-class-action='my-custom-class']").click();
    expect("[data-class-action='test']").toBeVisible();
});

test("hide/display option container base on selector", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderRow label="'Row 1'">
                <BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
            </BuilderRow>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".my-custom-class";
            static template = xml`<BuilderRow label="'Row 2'">
                <BuilderButton classAction="'test'"/>
            </BuilderRow>`;
        }
    );

    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".sub-child-target";
            static template = xml`<BuilderRow label="'Row 3'">
                <BuilderButton classAction="'another-custom-class'"/>
            </BuilderRow>`;
        }
    );

    await setupHTMLBuilder(`
        <div class="parent-target">
            <div class="child-target">
                <div class="sub-child-target">b</div>
            </div>
        </div>`);
    await contains(":iframe .sub-child-target").click();
    expect("[data-class-action='test']").not.toHaveCount();
    const selectorRowLabel = ".options-container .hb-row:not(.d-none) .hb-row-label";
    expect(queryAllTexts(selectorRowLabel)).toEqual(["Row 1", "Row 3"]);

    await contains("[data-class-action='my-custom-class']").click();
    expect("[data-class-action='test']").toBeVisible();
    expect(queryAllTexts(selectorRowLabel)).toEqual(["Row 1", "Row 2", "Row 3"]);
});

test("don't rerender the OptionsContainer every time you click on the same element", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderRow label="'Row 1'">
                <BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
            </BuilderRow>`;
        }
    );

    patchWithCleanup(OptionsContainer.prototype, {
        setup() {
            super.setup();
            onWillStart(() => {
                expect.step("onWillStart");
            });
        },
    });

    await setupHTMLBuilder(`
        <div class="parent-target">
            <div class="child-target">
                <div class="sub-child-target">b</div>
            </div>
        </div>`);
    await contains(":iframe .sub-child-target").click();
    expect("[data-class-action='test']").not.toHaveCount();
    expect.verifySteps(["onWillStart"]);

    await contains(":iframe .sub-child-target").click();
    expect.verifySteps([]);
});

test("no need to define 'isApplied' method for custom action if the widget already has a generic action", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            apply({ editingElement, value }) {
                editingElement.textContent = value;
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".s_test";
            static template = xml`
            <BuilderRow label.translate="Type">
                <BuilderSelect>
                    <BuilderSelectItem classAction="'A-class'" action="'customAction'" actionParam="'A'">A</BuilderSelectItem>
                </BuilderSelect>
            </BuilderRow>
        `;
        }
    );

    await setupHTMLBuilder(`
        <div class="s_test A-class">
        a
        </div>`);
    await contains(":iframe .s_test").click();
    expect(".options-container [data-class-action='A-class']").toHaveText("A");
});

test("useDomState callback shouldn't be called when the editingElement is removed", async () => {
    let editor;
    let count = 0;
    class TestOption extends BaseOptionComponent {
        static template = xml`<div class="test_option">test</div>`;
        static selector = ".s_test";
        static editableOnly = false;
        static props = {};

        setup() {
            useDomState(() => {
                expect.step(`useDomState ${count}`);
                return {
                    count: (count = count + 1),
                };
            });
        }
    }
    addBuilderOption(TestOption);
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = "*";
            static template = xml`<BuilderButton action="'addTestSnippet'">Add</BuilderButton>`;
        }
    );
    addBuilderAction({
        addTestSnippet: class extends BuilderAction {
            static id = "addTestSnippet";
            apply({ editingElement }) {
                const testEl = document.createElement("div");
                testEl.classList.add("s_test", "alert-info");
                testEl.textContent = "test";
                editingElement.after(testEl);
                editor.shared.builderOptions.setNextTarget(testEl);
            }
        },
    });

    const { getEditor } = await setupHTMLBuilder(`<div class="s_dummy">Hello</div>`);
    editor = getEditor();
    await contains(":iframe .s_dummy").click();
    await contains("[data-action-id='addTestSnippet']").click();
    expect(".options-container .test_option").toHaveCount(1);
    expect.verifySteps(["useDomState 0"]);

    undo(editor);
    await animationFrame();
    expect(".options-container .test_option").toHaveCount(0);
    expect.verifySteps([]);

    redo(editor);
    await animationFrame();
    expect(".options-container .test_option").toHaveCount(1);
    expect.verifySteps(["useDomState 1"]);
});

test("Update editing elements at dom change with multiple levels of applyTo", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            apply({ editingElement }) {
                const createdEl = editingElement.cloneNode(true);
                const parentEl = editingElement.parentElement;
                parentEl.appendChild(createdEl);
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderRow label="'Row 1'" applyTo="'.child-target'">
                <BuilderButton action="'customAction'" />
                <BuilderButton applyTo="'.sub-child-target'" classAction="'my-custom-class'"/>
            </BuilderRow>`;
        }
    );

    await setupHTMLBuilder(`
        <div class="parent-target">
            <div class="child-target">
                <div class="sub-child-target">b</div>
            </div>
        </div>`);
    await contains(":iframe .parent-target").click();
    await contains("[data-action-id='customAction']").click();
    await contains("[data-class-action='my-custom-class']").click();
    expect(":iframe .sub-child-target").toHaveClass("my-custom-class");
});

test("An option should only appear if its target is inside an editable area, unless specified otherwise", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-target";
            static template = xml`
                <BuilderButton classAction="'dummy-class-a'">Option A</BuilderButton>
            `;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-target";
            static editableOnly = false;
            static template = xml`
                <BuilderButton classAction="'dummy-class-b'">Option B</BuilderButton>
            `;
        }
    );
    const { getEditor } = await setupHTMLBuilder(`<div></div>`);
    const editor = getEditor();
    setContent(
        editor.editable,
        `<div class="content">
            <div class="test-target test-not-editable">NOT IN EDITABLE</div>
        </div>
        <div class="content o_editable">
            <div class="test-target test-editable">IN EDITABLE</div>
        </div>`
    );
    editor.shared.history.addStep();

    await contains(":iframe .test-not-editable").click();
    expect(queryAllTexts(".options-container [data-class-action]")).toEqual(["Option B"]);

    await contains(":iframe .test-editable").click();
    expect(queryAllTexts(".options-container [data-class-action]")).toEqual([
        "Option A",
        "Option B",
    ]);
});

describe("isActiveItem", () => {
    test("a button should not be visible if its dependency isn't (with undo)", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderButton attributeAction="'my-attribute1'" attributeActionValue="'x'" id="'id1'">b1</BuilderButton>
                    <BuilderButton attributeAction="'my-attribute1'" attributeActionValue="'y'"  id="'id2'">b2</BuilderButton>
                    <BuilderButton attributeAction="'my-attribute2'" attributeActionValue="'1'" t-if="this.isActiveItem('id1')">b3</BuilderButton>
                    <BuilderButton attributeAction="'my-attribute2'" attributeActionValue="'2'" t-if="this.isActiveItem('id2')">b4</BuilderButton>
                `;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        setSelection({
            anchorNode: queryFirst(":iframe .test-options-target").childNodes[0],
            anchorOffset: 0,
        });
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).not.toHaveCount();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).not.toHaveCount();
        await contains(
            "[data-attribute-action='my-attribute1'][data-attribute-action-value='x']"
        ).click();
        expect(":iframe .test-options-target").toHaveAttribute("my-attribute1", "x");
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).toBeVisible();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).not.toHaveCount();
        await contains(
            "[data-attribute-action='my-attribute1'][data-attribute-action-value='y']"
        ).click();
        expect(":iframe .test-options-target").toHaveAttribute("my-attribute1", "y");
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).not.toHaveCount();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).toBeVisible();
        await contains(".fa-undo").click();
        expect(":iframe .test-options-target").toHaveAttribute("my-attribute1", "x");
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).toBeVisible();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).not.toHaveCount();
        await contains(".fa-undo").click();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).not.toHaveCount();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).not.toHaveCount();
    });
    test("a button should not be visible if its dependency isn't (in a BuilderSelect with priority)", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderSelect>
                        <BuilderSelectItem classAction="'a'" id="'x'">x</BuilderSelectItem>
                        <BuilderSelectItem classAction="'a b'" id="'y'">y</BuilderSelectItem>
                    </BuilderSelect>
                    <BuilderButton classAction="'b1'" t-if="this.isActiveItem('x')">b1</BuilderButton>
                    <BuilderButton classAction="'b2'" t-if="this.isActiveItem('y')">b2</BuilderButton>
                `;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target a">a</div>`);
        setSelection({
            anchorNode: queryFirst(":iframe .test-options-target").childNodes[0],
            anchorOffset: 0,
        });
        await contains(":iframe .test-options-target").click();
        await animationFrame();
        expect(".options-container").toBeVisible();

        expect(".we-bg-options-container .dropdown").toHaveText("x");
        expect("[data-class-action='b1']").toBeVisible();
        expect("[data-class-action='b2']").not.toHaveCount();

        await contains(".we-bg-options-container .dropdown").click();
        await contains("[data-class-action='a b']").click();
        expect(".we-bg-options-container .dropdown").toHaveText("y");
        expect("[data-class-action='b1']").not.toHaveCount();
        expect("[data-class-action='b2']").toBeVisible();
    });
    test("a button should not be visible if the dependency is active", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderButton attributeAction="'my-attribute1'" attributeActionValue="'x'" id="'id1'">b1</BuilderButton>
                    <BuilderButton attributeAction="'my-attribute2'" attributeActionValue="'1'" t-if="!this.isActiveItem('id1')">b3</BuilderButton>
                `;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).toBeVisible();
        await contains(
            "[data-attribute-action='my-attribute1'][data-attribute-action-value='x']"
        ).click();
        expect(":iframe .test-options-target").toHaveAttribute("my-attribute1", "x");
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).not.toHaveCount();
    });
    test("a button should not be visible if the dependency is active (when a dependency is added after a dependent)", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderButton attributeAction="'my-attribute2'" attributeActionValue="'1'" t-if="this.isActiveItem('id')">b1</BuilderButton>
                    <BuilderButton attributeAction="'my-attribute2'" attributeActionValue="'2'" t-if="!this.isActiveItem('id')">b2</BuilderButton>
                    <BuilderRow label="'dependency'">
                        <BuilderButton attributeAction="'my-attribute1'" attributeActionValue="'x'" id="'id'">b3</BuilderButton>
                    </BuilderRow>
                `;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeVisible();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).not.toHaveCount();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).toBeVisible();
        await contains(
            "[data-attribute-action='my-attribute1'][data-attribute-action-value='x']"
        ).click();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='1']"
        ).toBeVisible();
        expect(
            "[data-attribute-action='my-attribute2'][data-attribute-action-value='2']"
        ).not.toHaveCount();
    });
    test("a button should not be visible if its dependency is removed from the DOM", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderButton classAction="'my-class1'" id="'id1'">b1</BuilderButton>
                    <BuilderButton classAction="'my-class2'" id="'id2'" t-if="this.isActiveItem('id1')">b2</BuilderButton>
                    <BuilderButton classAction="'my-class3'" t-if="this.isActiveItem('id2')">b3</BuilderButton>
                `;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target my-class1 my-class2">b</div>`);
        await contains(":iframe .test-options-target").click();
        await contains("[data-class-action='my-class1']").click();
        // Wait 2 animation frames: one for id2 to be removed and another for
        // id3 to be removed.
        await animationFrame();
        expect("[data-class-action='my-class3']").not.toHaveCount();
    });
});
