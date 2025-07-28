import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { describe, expect, test } from "@odoo/hoot";
import { fill } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

describe("classAction", () => {
    test("should reset when cliking on an empty classAction", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderButtonGroup>
                        <BuilderButton classAction="''"/>
                        <BuilderButton classAction="'x'"/>
                    </BuilderButtonGroup>
                `;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target x">a</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();

        expect("[data-class-action='x']").toHaveClass("active");

        await contains("[data-class-action='']").click();
        expect(":iframe .test-options-target").not.toHaveClass("x");
    });
    test("set multiples classes", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderButtonGroup>
                        <BuilderButton classAction="'x'"/>
                        <BuilderButton classAction="'x y z'"/>
                    </BuilderButtonGroup>
                `;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target x">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();

        expect("[data-class-action='x']").toHaveClass("active");
        expect("[data-class-action='x y z']").not.toHaveClass("active");

        await contains("[data-class-action='x y z']").click();
        expect(":iframe .test-options-target").toHaveClass("x y z");
        expect("[data-class-action='x']").not.toHaveClass("active");
        expect("[data-class-action='x y z']").toHaveClass("active");

        await contains("[data-class-action='x']").click();
        expect(":iframe .test-options-target").toHaveClass("x");
        expect(":iframe .test-options-target").not.toHaveClass("y z");
        expect("[data-class-action='x']").toHaveClass("active");
        expect("[data-class-action='x y z']").not.toHaveClass("active");
    });
    test("toggle class when not inside a BuilderButtonGroup", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderButton classAction="'x'"/>
                    <BuilderButtonGroup>
                        <BuilderButton classAction="'y'"/>
                    </BuilderButtonGroup>
                `;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">a</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();

        await contains("[data-class-action='x']").click();
        expect(":iframe .test-options-target").toHaveClass("x");
        await contains("[data-class-action='x']").click();
        expect(":iframe .test-options-target").not.toHaveClass("x");
        await contains("[data-class-action='y']").click();
        expect(":iframe .test-options-target").toHaveClass("y");
        await contains("[data-class-action='y']").click();
        expect(":iframe .test-options-target").toHaveClass("y");
    });
});

describe("styleAction", () => {
    test("should set a plain style", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderNumberInput styleAction="'width'" unit="'px'"
                    />
                `;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target" style="width: 10px;">a</div>`);
        await contains(":iframe .test-options-target").click();
        expect("input").toHaveValue("10");
        expect(".options-container").toBeDisplayed();
        expect(":iframe .test-options-target").toHaveStyle({ width: "10px" });
        expect(":iframe .test-options-target").toHaveAttribute("style", "width: 10px;"); // no !important

        await contains("input").click();
        await fill("1");
        expect("input").toHaveValue("101");
        expect(":iframe .test-options-target").toHaveStyle({ width: "101px" });
        expect(":iframe .test-options-target").toHaveAttribute("style", "width: 101px;"); // no !important

        await contains("input").edit("");
        expect(":iframe .test-options-target").toHaveAttribute("style", "width: 0px;");
    });
    test("should set a style with its associated class", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderNumberInput styleAction="{ mainParam: 'border-width', extraClass: 'border' }" unit="'px'" min="0" composable="true"
                    />
                `;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target border">a</div>`, {
            styleContent: ".border { border: solid; border-width: 1px !important; }",
        });
        await contains(":iframe .test-options-target").click();
        expect("input").toHaveValue("1");
        expect(".options-container").toBeDisplayed();
        expect(":iframe .test-options-target").not.toHaveAttribute("style");

        await contains("input").click();
        await fill("2");
        expect("input").toHaveValue("12");
        expect(":iframe .test-options-target").toHaveAttribute(
            "style",
            "border-width: 12px !important;"
        );
        expect(":iframe .test-options-target").toHaveClass("border");

        await contains("input").edit("0");
        expect(":iframe .test-options-target").not.toHaveAttribute("style");
        expect(":iframe .test-options-target").not.toHaveClass("border");

        await contains("input").edit("1");
        expect(":iframe .test-options-target").toHaveAttribute("style", "");
        expect(":iframe .test-options-target").toHaveClass("border");
    });
    test("should set a composite style with its associated class", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderNumberInput styleAction="{ mainParam: 'border-width', extraClass: 'border' }" unit="'px'" min="0" composable="true"
                    />
                `;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target">a</div>`, {
            styleContent: ".border { border: solid; border-width: 1px !important; }",
        });
        await contains(":iframe .test-options-target").click();
        expect("input").toHaveValue("0");
        expect(".options-container").toBeDisplayed();
        expect(":iframe .test-options-target").not.toHaveAttribute("style");

        await contains("input").edit("10");
        expect(":iframe .test-options-target").toHaveAttribute(
            "style",
            "border-width: 10px !important;"
        );
        expect(":iframe .test-options-target").toHaveClass("border");

        await contains("input").edit("10 20");
        expect(":iframe .test-options-target").toHaveAttribute(
            "style",
            "border-width: 10px 20px !important;"
        );
        expect(":iframe .test-options-target").toHaveClass("border");

        await contains("input").edit("10 20 30");
        expect(":iframe .test-options-target").toHaveAttribute(
            "style",
            "border-width: 10px 20px 30px !important;"
        );
        expect(":iframe .test-options-target").toHaveClass("border");

        await contains("input").edit("10 20 30 40");
        expect(":iframe .test-options-target").toHaveAttribute(
            "style",
            "border-width: 10px 20px 30px 40px !important;"
        );
        expect(":iframe .test-options-target").toHaveClass("border");

        await contains("input").edit("10 1");
        expect(":iframe .test-options-target").toHaveAttribute(
            "style",
            "border-bottom-width: 10px !important; border-top-width: 10px !important;"
        );
        expect(":iframe .test-options-target").toHaveClass("border");

        await contains("input").edit("1 10");
        expect(":iframe .test-options-target").toHaveAttribute(
            "style",
            "border-left-width: 10px !important; border-right-width: 10px !important;"
        );
        expect(":iframe .test-options-target").toHaveClass("border");

        await contains("input").edit("1 10 10");
        expect(":iframe .test-options-target").toHaveAttribute(
            "style",
            "border-left-width: 10px !important; border-bottom-width: 10px !important; border-right-width: 10px !important;"
        );
        expect(":iframe .test-options-target").toHaveClass("border");

        await contains("input").edit("1 1 1 10");
        expect(":iframe .test-options-target").toHaveAttribute(
            "style",
            "border-left-width: 10px !important;"
        );
        expect(":iframe .test-options-target").toHaveClass("border");
    });

    test("button isApplied is properly computed with percentage width values", async () => {
        addBuilderOption(
            class extends BaseOptionComponent {
                static selector = ".test-options-target";
                static template = xml`
                    <BuilderButtonGroup styleAction="'width'">
                        <BuilderButton styleActionValue="''">Default</BuilderButton>
                        <BuilderButton styleActionValue="'50%'">50%</BuilderButton>
                    </BuilderButtonGroup>
                `;
            }
        );
        await setupHTMLBuilder(`<div class="test-options-target x">a</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();

        expect("[data-style-action-value='']").toHaveClass("active");
        expect("[data-style-action-value='50%']").not.toHaveClass("active");
        expect(":iframe .test-options-target").toHaveOuterHTML(
            `<div class="test-options-target x"> a </div>`
        );

        await contains("[data-style-action-value='50%']").click();

        expect(":iframe .test-options-target").toHaveOuterHTML(
            `<div class="test-options-target x" style="width: 50% !important;"> a </div>`
        );
        expect("[data-style-action-value='']").not.toHaveClass("active");
        expect("[data-style-action-value='50%']").toHaveClass("active");
    });
});
