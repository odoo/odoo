import { describe, expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";

defineWebsiteModels();

describe("classAction", () => {
    test("should reset when cliking on an empty classAction", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`
                    <BuilderButtonGroup>
                        <BuilderButton classAction="''"/>
                        <BuilderButton classAction="'x'"/>
                    </BuilderButtonGroup>
                `,
        });
        await setupWebsiteBuilder(`<div class="test-options-target x">a</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();

        expect("[data-class-action='x']").toHaveClass("active");

        await contains("[data-class-action='']").click();
        expect(":iframe .test-options-target").not.toHaveClass("x");
    });
    test("set multiples classes", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`
                    <BuilderButtonGroup>
                        <BuilderButton classAction="'x'"/>
                        <BuilderButton classAction="'x y z'"/>
                    </BuilderButtonGroup>
                `,
        });
        await setupWebsiteBuilder(`<div class="test-options-target x">b</div>`);
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
        addOption({
            selector: ".test-options-target",
            template: xml`
                    <BuilderButton classAction="'x'"/>
                    <BuilderButtonGroup>
                        <BuilderButton classAction="'y'"/>
                    </BuilderButtonGroup>
                `,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">a</div>`);
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
