import { describe, expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../helpers";

defineWebsiteModels();

describe("builder shorthand actions", () => {
    describe("classAction", () => {
        test("set multiples classes", async () => {
            addOption({
                selector: ".test-options-target",
                template: xml`
                    <WeButtonGroup>
                        <WeButton classAction="'x'"/>
                        <WeButton classAction="'x y z'"/>
                    </WeButtonGroup>
                `,
            });
            await setupWebsiteBuilder(`<div class="test-options-target x">b</div>`);
            await contains(":iframe .test-options-target").click();
            expect(".options-container").toBeDisplayed();

            expect("[data-class-action='x']").toHaveClass("active");
            expect("[data-class-action='x y z']").not.toHaveClass("active");

            await contains("[data-class-action='x y z']").click();
            expect(":iframe .test-options-target").toHaveClass("x y z");
            expect("[data-class-action='x']").toHaveClass("active");
            expect("[data-class-action='x y z']").toHaveClass("active");

            await contains("[data-class-action='x']").click();
            expect(":iframe .test-options-target").toHaveClass("x");
            expect(":iframe .test-options-target").not.toHaveClass("y z");
            expect("[data-class-action='x']").toHaveClass("active");
            expect("[data-class-action='x y z']").not.toHaveClass("active");
        });
        test("toggle class when not inside a WeButtonGroup", async () => {
            addOption({
                selector: ".test-options-target",
                template: xml`
                    <WeButton classAction="'x'"/>
                    <WeButtonGroup>
                        <WeButton classAction="'y'"/>
                    </WeButtonGroup>
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
});
