import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
    editBuilderRangeValue,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { describe, expect, test } from "@odoo/hoot";
import {
    advanceTime,
    animationFrame,
    clear,
    click,
    fill,
    freezeTime,
    queryFirst,
} from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";
import { xml } from "@odoo/owl";
import { contains, defineModels, models } from "@web/../tests/web_test_helpers";
import { BaseOptionComponent } from "@html_builder/core/utils";

describe.current.tags("desktop");

test("should get the initial value of the input", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue({ editingElement }) {
                return editingElement.innerHTML;
            }
            apply({ params }) {
                expect.step(`customAction ${params}`);
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderNumberInput action="'customAction'"/>`;
        }
    );
    await setupHTMLBuilder(`
                <div class="test-options-target">10</div>
            `);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    const input = queryFirst(".options-container input");
    expect(input).toHaveValue("10");
});
test("hide/display base on applyTo", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderNumberInput applyTo="'.my-custom-class'" action="'customAction'"/>`;
        }
    );
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue() {
                return "10";
            }
        },
    });

    const { getEditableContent } = await setupHTMLBuilder(
        `<div class="parent-target"><div class="child-target">b</div></div>`
    );
    const editableContent = getEditableContent();
    await contains(":iframe .parent-target").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect("[data-action-id='customAction']").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target my-custom-class">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect("[data-action-id='customAction']").toHaveCount(1);
    expect("[data-action-id='customAction'] input").toHaveValue("10");
});
test("input with classAction and styleAction", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderNumberInput classAction="'testAction'" styleAction="'--custom-property'"/>`;
        }
    );
    await setupHTMLBuilder(`
                <div class="test-options-target">10</div>
            `);
    await contains(":iframe .test-options-target").click();
    await contains(".options-container input").edit("2");
    expect(":iframe .test-options-target").toHaveStyle({
        "--custom-property": "2",
    });
});

test("input kept on async action", async () => {
    const def = new Deferred();
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue({ editingElement }) {
                return editingElement.dataset.test;
            }
            async apply({ editingElement, value }) {
                await def;
                editingElement.dataset.test = value;
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderNumberInput action="'customAction'"/>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target" data-test="1">Hello</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".options-container input").edit("2");
    await contains(".options-container input").fill(3, { confirm: false });
    def.resolve();
    await animationFrame();
    expect(".options-container input").toHaveValue("23");
});

test("input should remove invalid char", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            setup() {
                this.preview = false;
            }
            getValue({ editingElement }) {
                return editingElement.dataset.test;
            }
            async apply({ editingElement, value }) {
                editingElement.dataset.test = value;
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderNumberInput action="'customAction'"/>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target-composable";
            static template = xml`<BuilderNumberInput action="'customAction'" composable="true"/>`;
        }
    );
    await setupHTMLBuilder(
        `<div class="test-options-target" data-test="1">Hello</div><div class="test-options-target-composable" data-test="2">World</div>`
    );

    // Single
    await contains(":iframe .test-options-target").click();

    await contains(".options-container:first input").edit("-1-2-");
    await animationFrame();
    expect(".options-container:first input").toHaveValue("-12");

    await contains(".options-container:first input").edit("3-4-5");
    await animationFrame();
    expect(".options-container:first input").toHaveValue("345");

    await contains(".options-container:first input").edit(" .$a?,6.b$?,7.$?c,  ");
    await animationFrame();
    expect(".options-container:first input").toHaveValue("0.67");

    // Composable
    await contains(":iframe .test-options-target-composable").click();

    await contains(".options-container:last input").edit("-12 12 -12 12");
    await animationFrame();
    expect(".options-container:last input").toHaveValue("-12 12 -12 12");

    await contains(".options-container:last input").edit("3?/4.5 34,/?5");
    await animationFrame();
    expect(".options-container:last input").toHaveValue("34.5 34.5");

    await contains(".options-container:last input").edit("  6bc7 6//7 6$a7 6d7  ");
    await animationFrame();
    expect(".options-container:last input").toHaveValue("67 67 67 67");
});

describe("default value", () => {
    test("should use the default value when there is no value onChange", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ value }) {
                    expect.step(`customAction ${value}`);
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" default="20"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target">10</div>
        `);
        await contains(":iframe .test-options-target").click();
        await editBuilderRangeValue(".options-container input", "");

        expect.verifySteps(["customAction 20", "customAction 20"]);
        expect(".options-container input").toHaveValue("20");
    });
    test("clear BuilderNumberInput without default value", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" />`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">10</div>
                `);
        await contains(":iframe .test-options-target").click();
        await click("[data-action-id='customAction'] input");
        expect("[data-action-id='customAction'] input").toHaveValue("10");

        await clear();
        expect("[data-action-id='customAction'] input").toHaveValue("");
        expect(":iframe .test-options-target").toHaveInnerHTML("0"); //Check that default value is used during preview
        await click(".options-container");
        expect("[data-action-id='customAction'] input").toHaveValue("0");
        expect(":iframe .test-options-target").toHaveInnerHTML("0");
    });
    test("clear BuilderNumberInput with default value", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" default="1"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">10</div>
                `);
        await contains(":iframe .test-options-target").click();
        await click("[data-action-id='customAction'] input");
        expect("[data-action-id='customAction'] input").toHaveValue("10");

        await clear();
        await click(".options-container");
        expect("[data-action-id='customAction'] input").toHaveValue("1");
        expect(":iframe .test-options-target").toHaveInnerHTML("1");
    });
    test("clear BuilderNumberInput with null default value", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerText;
                }
                apply({ editingElement, value }) {
                    editingElement.innerText = value;
                    if (value === null) {
                        editingElement.innerText = "10";
                    }
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" default="null"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">10</div>
                `);
        await contains(":iframe .test-options-target").click();
        await click("[data-action-id='customAction'] input");
        expect("[data-action-id='customAction'] input").toHaveValue(10);

        await contains("[data-action-id='customAction'] input").edit("5");
        expect(":iframe .test-options-target").toHaveInnerHTML("5");

        await clear();
        await click(".options-container");
        await animationFrame();
        expect(":iframe .test-options-target").toHaveInnerHTML("10");
        expect("[data-action-id='customAction'] input").toHaveValue("10");
    });
});
describe("operations", () => {
    test("should preview changes", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">10</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        await fill("2");
        expect.verifySteps(["customAction 102"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("102");
        expect(".o-snippets-top-actions .fa-undo").not.toBeEnabled();
        expect(".o-snippets-top-actions .fa-repeat").not.toBeEnabled();
    });
    test("should commit changes", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">10</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        await fill("2");
        expect.verifySteps(["customAction 102"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("102");
        await click(document.body);
        await animationFrame();
        expect.verifySteps(["customAction 102"]);
        expect(".o-snippets-top-actions .fa-undo").toBeEnabled();
        expect(".o-snippets-top-actions .fa-repeat").not.toBeEnabled();
    });
    test("should commit changes after an undo", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">10</div>
                `);
        await contains(":iframe .test-options-target").click();
        await click(".options-container input");
        await fill(2);
        expect(":iframe .test-options-target").toHaveInnerHTML("102");
        await click(document.body);
        expect.verifySteps(["customAction 102", "customAction 102"]);
        await animationFrame();
        click(".o-snippets-top-actions .fa-undo");
        await animationFrame();
        expect(":iframe .test-options-target").toHaveInnerHTML("10");
        await click(".options-container input");
        await fill("2");
        expect(":iframe .test-options-target").toHaveInnerHTML("102");
        await click(document.body);
        expect.verifySteps(["customAction 102", "customAction 102"]);
    });
    test("should not commit on input if no preview", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" preview="false"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">10</div>
                `);
        await contains(":iframe .test-options-target").click();
        await click(".options-container input");
        await fill(2);
        expect(":iframe .test-options-target").toHaveInnerHTML("10");
        await click(document.body);
        expect.verifySteps(["customAction 102"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("102");
    });
});
describe("keyboard triggers", () => {
    test("input should step up or down from by the step prop", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" step="2"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target">10</div>
        `);
        await contains(":iframe .test-options-target").click();

        // simulate arrow up
        await contains(".options-container input").keyDown("ArrowUp");
        await advanceTime();
        expect(":iframe .test-options-target").toHaveInnerHTML("12");

        // simulate arrow down
        await contains(".options-container input").keyDown("ArrowDown");
        await advanceTime();
        expect(":iframe .test-options-target").toHaveInnerHTML("10");

        expect.verifySteps(["customAction 12", "customAction 10"]);
    });
    test("multi values: apply change on each value with up or down", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" composable="true"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target">10 4 0</div>
        `);
        await contains(":iframe .test-options-target").click();

        // simulate arrow up
        await contains(".options-container input").focus();
        await contains(".options-container input").keyDown("ArrowUp");
        await advanceTime();
        expect(":iframe .test-options-target").toHaveInnerHTML("11 5 1");

        // simulate arrow down
        await contains(".options-container input").keyDown("ArrowDown");
        await advanceTime();
        expect(":iframe .test-options-target").toHaveInnerHTML("10 4 0");

        expect.verifySteps(["customAction 11 5 1", "customAction 10 4 0"]);
    });
    test("up on empty BuilderNumberInput gives 1", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.dataset.number;
                }
                apply({ editingElement, value }) {
                    editingElement.dataset.number = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" />`;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">Non empty div.</div>`);
        await contains(":iframe .test-options-target").click();
        await click("[data-action-id='customAction'] input");
        await clear();
        expect("[data-action-id='customAction'] input").toHaveValue("");

        await contains("[data-action-id='customAction'] input").keyDown("ArrowUp");
        expect("[data-action-id='customAction'] input").toHaveValue("1");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "1");
    });
    test("down on empty BuilderNumberInput gives -1", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.dataset.number;
                }
                apply({ editingElement, value }) {
                    editingElement.dataset.number = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" />`;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">Non empty div.</div>`);
        await contains(":iframe .test-options-target").click();
        await click("[data-action-id='customAction'] input");
        await clear();
        expect("[data-action-id='customAction'] input").toHaveValue("");

        await contains("[data-action-id='customAction'] input").keyDown("ArrowDown");
        await animationFrame();
        expect("[data-action-id='customAction'] input").toHaveValue("-1");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "-1");
    });
    test("apply preview on keydown and debounce commit operation", async () => {
        freezeTime();
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target">10</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").focus();
        // Simulate a single keydown hold down for a while.
        await contains(".options-container input").keyDown("ArrowUp");
        await advanceTime(500); // Default browser delay between 1st & 2nd keydown.
        await contains(".options-container input").keyDown("ArrowUp");
        await advanceTime(50);
        await contains(".options-container input").keyDown("ArrowUp");
        await advanceTime(50);
        expect(":iframe .test-options-target").toHaveInnerHTML("13");
        // 3 previews
        expect.verifySteps(["customAction 11", "customAction 12", "customAction 13"]);
        await advanceTime(560); // Debounce = 550
        // 1 commit
        expect.verifySteps(["customAction 13"]);
    });
});
describe("unit & saveUnit", () => {
    test("should handle unit", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" unit="'px'"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">5px</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        const input = queryFirst(".options-container input");
        expect(input).toHaveValue("5");
        await fill(1);
        expect.verifySteps(["customAction 51px"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("51px");
    });
    test("should handle saveUnit", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" unit="'s'" saveUnit="'ms'"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">5000ms</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        const input = queryFirst(".options-container input");
        expect(input).toHaveValue("5");
        await fill("7");
        expect.verifySteps(["customAction 57000ms"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("57000ms");
    });
    test("should handle saveUnit even without explicit unit", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" unit="'s'" saveUnit="'ms'"/>`;
            }
        );
        // note that 5000 has no unit of measure
        await setupHTMLBuilder(`
                    <div class="test-options-target">5000</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        const input = queryFirst(".options-container input");
        expect(input).toHaveValue("5");
    });
    test("should handle empty saveUnit", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" unit="'px'" saveUnit="''"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">5</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        const input = queryFirst(".options-container input");
        expect(input).toHaveValue("5");
        await fill(1);
        expect.verifySteps(["customAction 51"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("51");
    });
    test("should handle savedUnit", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerText;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.innerText = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" unit="'s'" saveUnit="'ms'"/>`;
            }
        );
        await setupHTMLBuilder(`
                    <div class="test-options-target">5s</div>
                `);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await click(".options-container input");
        const input = queryFirst(".options-container input");
        expect(input).toHaveValue("5");
        await fill("7");
        expect.verifySteps(["customAction 57000ms"]);
        expect(":iframe .test-options-target").toHaveInnerHTML("57000ms");
    });
});
describe("sanitized values", () => {
    test("don't allow multi values by default", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ editingElement, value }) {
                    editingElement.innerHTML = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target">10</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("33 4 0", { instantly: true });
        expect(".options-container input").toHaveValue("33");
        expect(":iframe .test-options-target").toHaveInnerHTML("33");
    });
    test("use min when the given value is smaller", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ value }) {
                    expect.step(`customAction ${value}`);
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" min="0"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target">10</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("-1", { instantly: true });
        expect.verifySteps(["customAction 0", "customAction 0"]); // input, change
        expect(".options-container input").toHaveValue("0");
    });
    test("clamp to min value when pressing down arrow with min > 0", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.textContent;
                }
                apply({ editingElement, value }) {
                    expect.step(`customAction ${value}`);
                    editingElement.textContent = value;
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" min="1"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target">2</div>
        `);
        await contains(":iframe .test-options-target").click();
        // Simulate pressing arrow down
        await contains(".options-container input").keyDown("ArrowDown");
        expect.verifySteps(["customAction 1"]);
        expect(".options-container input").toHaveValue("1");
        expect(":iframe .test-options-target").toHaveText("1");
        // Pressing down again should stay at min value
        await contains(".options-container input").keyDown("ArrowDown");
        expect.verifySteps(["customAction 1"]);
        expect(".options-container input").toHaveValue("1");
        expect(":iframe .test-options-target").toHaveText("1");
    });
    test("use max when the given value is bigger", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ value }) {
                    expect.step(`customAction ${value}`);
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" max="10"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target">3</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("11", { instantly: true });
        await animationFrame();
        expect.verifySteps(["customAction 0", "customAction 10"]); // input, change
        expect(".options-container input").toHaveValue("10");
    });
    test("multi values: trailing space in BuilderNumberInput is ignored", async () => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.innerHTML;
                }
                apply({ value }) {
                    expect.step(`customAction ${value}`);
                }
            },
        });
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput action="'customAction'" composable="true"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target">10</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").fill("3 4 5 ", { instantly: true });
        expect.verifySteps(["customAction 3 4 5", "customAction 3 4 5"]); // input, change
        expect(".options-container input").toHaveValue("3 4 5");
    });
    test("after input, displayed value is cleaned to match only numbers", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput dataAttributeAction="'number'"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target" data-number="10">Test</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit(" a&$*+>");
        expect(".options-container input").toHaveValue("0");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "0");
    });
    test("after input, displayed value is cleaned to match only numbers (default=null)", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput dataAttributeAction="'number'" default="null"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target" data-number="10">Test</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit(" a&$*+>");
        expect(".options-container input").toHaveValue("");
        expect(":iframe .test-options-target").not.toHaveAttribute("data-number");
    });
    test("after copy / pasting, displayed value is cleaned to match only numbers", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput dataAttributeAction="'number'"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target" data-number="10">Test</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit(" a&$*-3+>", { instantly: true });
        expect(".options-container input").toHaveValue("-3");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "-3");
    });
    test("accept decimal numbers", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput dataAttributeAction="'number'"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target" data-number="10">Test</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("3.3");
        expect(".options-container input").toHaveValue("3.3");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "3.3");
    });
    test("BuilderNumberInput transforms , into .", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput dataAttributeAction="'number'"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target" data-number="10">Test</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("3,3");
        expect(".options-container input").toHaveValue("3.3");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "3.3");
    });
    test("displays the correct value (no floating point precision error)", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput dataAttributeAction="'number'" step="0.1"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target" data-number="10">Test</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("0.2");
        expect(".options-container input").toHaveValue("0.2");
        // simulate arrow keys
        await contains(".options-container input").keyDown("ArrowUp");
        await advanceTime();
        expect(".options-container input").toHaveValue("0.3");
        await contains(".options-container input").keyDown("ArrowDown");
        await advanceTime();
        expect(".options-container input").toHaveValue("0.2");
    });
    test("rounds the number to 3 decimals", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput dataAttributeAction="'number'"/>`;
            }
        );
        await setupHTMLBuilder(`
            <div class="test-options-target" data-number="10">Test</div>
        `);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("3.33333333333");
        expect(".options-container input").toHaveValue("3.333");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "3.333");

        await contains(".options-container input").edit("1.284778323");
        expect(".options-container input").toHaveValue("1.285");
        expect(":iframe .test-options-target").toHaveAttribute("data-number", "1.285");
    });
    test("should save font with full precision in rem and display to correct value in px", async () => {
        class WebEditorAssets extends models.Model {
            _name = "web_editor.assets";
            make_scss_customization() {}
        }
        defineModels([WebEditorAssets]);
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`<BuilderNumberInput dataAttributeAction="'number'" unit="'px'" saveUnit="'rem'"/>`;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">Test</div>`);
        await contains(":iframe .test-options-target").click();
        await contains(".options-container input").edit("19");
        expect(".options-container input").toHaveValue("19");
    });
});
