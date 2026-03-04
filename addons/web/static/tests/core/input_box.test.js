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
        expect(".o_input_box").toHaveStyle({"--inputbox-overlay-start-size": "0px", "--inputbox-overlay-end-size": 2 * overlayPadding + "px"});
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
        expect(".o_input_box").toHaveStyle({"--inputbox-overlay-start-size": "0px", "--inputbox-overlay-end-size": overlayPadding + "px"});
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
        expect(".o_input_box:not(.o_input_box .o_input_box").toHaveAttribute("style",`--inputbox-overlay-start-size: ${overlayPaddingStart}px; --inputbox-overlay-end-size: ${overlayPaddingEnd}px;`);
        expect(".o_input_box .o_input_box").not.toHaveAttribute("style");
        expect(".o_input_box .fa-phone").toBeVisible();
    });

    test("InputBox overlays that are invisible don't affect the padding", async () => {
        class Root extends Component {
            static components = {};
            static props = {};
            static template = xml`
                <div class="o_input_box">
                    <i class="o_input_box_overlay_start fa fa-phone d-none d-touch-block"/>
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
        const overlayPaddingEnd = queryFirst(".o_input_box_overlay_end").clientWidth + INPUTBOX_SPACING_UNIT;
        expect(".o_input_box:not(.o_input_box .o_input_box").toHaveAttribute("style",`--inputbox-overlay-start-size: 0px; --inputbox-overlay-end-size: ${overlayPaddingEnd}px;`);
        expect(".o_input_box .fa-phone").not.toBeVisible();
    });

    test("Multiple and different overlay items can be present", async () => {
        const CUSTOM_PADDING_AROUND = 5;
        // In this test, we use the --inputbox-overlay-padding-x variable to add horizontal padding around the inputbox element.
        // This is the implementation used by the form view on touch devices to add spacing around the entire box.
        const item_a_w = 24;
        const item_b_w = 35;
        const item_c_w = 50;
        class Root extends Component {
            static components = {};
            static props = {};
            static template = xml`
                <div class="o_input_box" style="--inputbox-overlay-padding-x: ${CUSTOM_PADDING_AROUND}px;">
                    <div class="o_input_box_overlay_start" style="width: ${item_a_w}px;"/>
                    <div class="o_input_box">
                        <span>Hello Guys</span>
                        <div id="b" class="o_input_box_overlay_end" style="width: ${item_b_w}px;"/>
                        <div id="c" class="o_input_box_overlay_end" style="width: ${item_c_w}px;"/>
                    </div>
                </div>
            `;
        }
        await mountWithCleanup(Root);
        // Component with o_input_box class having o_input_box_overlay elements must call the positioning function after the render
        positionInputBoxOverlay(getFixture());
        await animationFrame();
        expect(".o_input_box .o_input_box_overlay_start").toHaveCount(1);
        expect(".o_input_box .o_input_box_overlay_end").toHaveCount(2);
        const overlayPaddingStart = queryFirst(".o_input_box_overlay_start").clientWidth + INPUTBOX_SPACING_UNIT;
        const overlayPaddingEnd = queryFirst(".o_input_box_overlay_end#b").clientWidth + 2 * INPUTBOX_SPACING_UNIT + queryFirst(".o_input_box_overlay_end#c").clientWidth;
        expect(".o_input_box:not(.o_input_box .o_input_box").toHaveAttribute("style",`--inputbox-overlay-padding-x: ${CUSTOM_PADDING_AROUND}px; --inputbox-overlay-start-size: ${overlayPaddingStart}px; --inputbox-overlay-end-size: ${overlayPaddingEnd}px;`);
        expect(".o_input_box .o_input_box").not.toHaveAttribute("style");
        expect(getComputedStyle(queryFirst(".o_input_box")).paddingInlineStart).toBe(`${overlayPaddingStart + 1.5 * CUSTOM_PADDING_AROUND}px`);
        expect(getComputedStyle(queryFirst(".o_input_box")).paddingInlineEnd).toBe(`${overlayPaddingEnd + CUSTOM_PADDING_AROUND}px`);
    });
});
