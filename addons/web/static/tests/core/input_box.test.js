import { describe, test, expect, getFixture } from "@odoo/hoot";
import { animationFrame, queryFirst } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { InputBox, positionInputBoxOverlay } from "@web/core/input_box/input_box";

const INPUTBOX_SPACING_UNIT = 8;

describe("InputBox Component", () => {
    test.tags("desktop");
    test("basic rendering of the InputBox component on desktop", async () => {
        await mountWithCleanup(InputBox, {
            props: {
                type: "text",
                placeholder: "A Placeholder",
                overlayButtons: [
                    {
                        icon: "fa-building",
                        onSelected: () => expect.step("building selected"),
                        name: "My Icon"
                    },
                    {
                        icon: "fa-trash",
                        onSelected: () => expect.step("trash selected"),
                        name: "My Trash"
                    },
                ]
            },
        });
        // Component with o_input_box class having o_input_box_overlay elements must call the positioning function after the render
        positionInputBoxOverlay(getFixture());
        await animationFrame();
        expect(".o_input_box").toHaveCount(1);
        expect(".o_input_box .o_input_box_overlay_end.btn").toHaveCount(2);
        expect(".o_input_box .btn .fa-building").not.toBeVisible();
        expect(".o_input_box .btn .fa-trash").not.toBeVisible();
        const overlayPadding = queryFirst(".o_input_box_overlay_end").clientWidth + INPUTBOX_SPACING_UNIT;
        expect(".o_input_box").toHaveStyle({"--inputbox-overlay-padding-prefix": "0px", "--inputbox-overlay-padding-suffix": 2 * overlayPadding + "px"});
        expect(".o_input_box .o_input_box_overlay_end:eq(0)").toHaveStyle({"inset-inline-end": overlayPadding + "px"});
        expect(".o_input_box .o_input_box_overlay_end:eq(1)").toHaveStyle({"inset-inline-end": "0px"});
        await contains(".o_input_box input").click();
        expect(".o_input_box .btn .fa-building").toBeVisible();
        expect(".o_input_box .btn .fa-trash").toBeVisible();
        await contains(".o_input_box .fa-building").click();
        expect.verifySteps(["building selected"]);
    });

    test.tags("mobile");
    test("basic rendering of the InputBox component on mobile", async () => {
        await mountWithCleanup(InputBox, {
            props: {
                type: "text",
                placeholder: "A Placeholder",
                overlayButtons: [
                    {
                        icon: "fa-building",
                        onSelected: () => expect.step("building selected"),
                        name: "My Icon"
                    },
                    {
                        icon: "fa-trash",
                        onSelected: () => expect.step("trash selected"),
                        name: "My Trash"
                    },
                ]
            },
        });
        // Component with o_input_box class having o_input_box_overlay elements must call the positioning function after the render
        positionInputBoxOverlay(getFixture());
        await animationFrame();
        expect(".o_input_box").toHaveCount(1);
        expect(".o_input_box .o_input_box_overlay_end.btn").toHaveCount(1);
        expect(".o_input_box .btn .fa-building").toHaveCount(0);
        expect(".o_input_box .btn .fa-trash").toHaveCount(0);
        await animationFrame();
        expect(".o_input_box .btn .oi-ellipsis-v").toBeVisible();
        const overlayPadding = queryFirst(".o_input_box_overlay_end").clientWidth + INPUTBOX_SPACING_UNIT;
        expect(".o_input_box").toHaveStyle({"--inputbox-overlay-padding-prefix": "0px", "--inputbox-overlay-padding-suffix": overlayPadding + "px"});
        await contains(".o_input_box .btn .oi-ellipsis-v").click();
        await animationFrame();
        expect(".o_bottom_sheet").toHaveCount(1);
        expect(".dropdown-item:contains(My Icon)").toBeVisible();
        expect(".dropdown-item:contains(My Trash)").toBeVisible();
        await contains(".dropdown-item:contains(My Icon)").click();
        expect.verifySteps(["building selected"]);
    });
});

describe("Elements with o_input_box classname", () => {
    test("Only the highest o_input_box element is considered as the root box", async () => {
        class Root extends Component {
            static components = {};
            static props = {};
            static template = xml`
                <div class="o_input_box">
                    <i class="o_input_box_overlay_start fa fa-phone"/>
                    <div class="o_input_box">
                        <span>0123456</span>
                        <i class="o_input_box_overlay_end fa fa-arrow"/>
                    </div>
                </div>
            `;
        }
        await mountWithCleanup(Root);
        // Component with o_input_box class having o_input_box_overlay elements must call the positioning function after the render
        positionInputBoxOverlay(getFixture());
        await animationFrame();
        expect(".o_input_box .fa").toHaveCount(2);
        const overlayPaddingStart = queryFirst(".o_input_box_overlay_start").clientWidth + INPUTBOX_SPACING_UNIT;
        const overlayPaddingEnd = queryFirst(".o_input_box_overlay_end").clientWidth + INPUTBOX_SPACING_UNIT;
        expect(".o_input_box:not(.o_input_box .o_input_box").toHaveAttribute("style",`--inputbox-overlay-padding-prefix: ${overlayPaddingStart}px; --inputbox-overlay-padding-suffix: ${overlayPaddingEnd}px;`);
        expect(".o_input_box .o_input_box").not.toHaveAttribute("style");
        expect(".o_input_box .fa-phone").toBeVisible();
    });
});
