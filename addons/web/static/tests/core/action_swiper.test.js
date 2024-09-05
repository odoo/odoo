/** @odoo-module alias=@web/../tests/mobile/core/action_swiper_tests default=false */

import { Component, onPatched, xml } from "@odoo/owl";
import { Deferred } from "@web/core/utils/concurrency";
import { ActionSwiper } from "@web/core/action_swiper/action_swiper";
import { beforeEach, expect, test } from "@odoo/hoot";
import { defineParams } from "../_framework/mock_server/mock_server";
import {
    contains,
    defineStyle,
    mountWithCleanup,
    patchWithCleanup,
    swipeLeft,
    swipeRight,
} from "@web/../tests/web_test_helpers";
import { queryFirst, hover } from "@odoo/hoot-dom";
import { advanceTime, animationFrame, mockTouch } from "@odoo/hoot-mock";

beforeEach(() => {
    mockTouch(true);
    // Disable action swiper transitions
    defineStyle(/* css */ `
        .o_actionswiper_target_container {
            transition: none !important;
        }
    `);
});

// Tests marked as will fail on browsers that don't support
// TouchEvent by default. It might be an option to activate on some browser.

test("render only its target if no props is given", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { ActionSwiper };
        static template = xml`
                <div class="d-flex">
                    <ActionSwiper>
                        <div class="target-component"/>
                    </ActionSwiper>
                </div>
            `;
    }
    await mountWithCleanup(Parent);
    expect("div.o_actionswiper").toHaveCount(0);
    expect("div.target-component").toHaveCount(1);
});

test("only render the necessary divs", async () => {
    await mountWithCleanup(ActionSwiper, {
        props: {
            onRightSwipe: {
                action: () => {},
                icon: "fa-circle",
                bgColor: "bg-warning",
            },
            slots: {},
        },
    });
    expect("div.o_actionswiper_right_swipe_area").toHaveCount(1);
    expect("div.o_actionswiper_left_swipe_area").toHaveCount(0);
    await mountWithCleanup(ActionSwiper, {
        props: {
            onLeftSwipe: {
                action: () => {},
                icon: "fa-circle",
                bgColor: "bg-warning",
            },
            slots: {},
        },
    });
    expect("div.o_actionswiper_right_swipe_area").toHaveCount(1);
    expect("div.o_actionswiper_left_swipe_area").toHaveCount(1);
});

test("render with the height of its content", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { ActionSwiper };
        static template = xml`
                <div class="o-container d-flex" style="width: 200px; height: 200px; overflow: auto">
                    <ActionSwiper onRightSwipe = "{
                        action: () => this.onRightSwipe(),
                        icon: 'fa-circle',
                        bgColor: 'bg-warning'
                    }">
                        <div class="target-component" style="height: 800px">This element is very high and
                        the o-container element must have a scrollbar</div>
                    </ActionSwiper>
                </div>
            `;
        onRightSwipe() {
            expect.step("onRightSwipe");
        }
    }
    await mountWithCleanup(Parent);
    expect(queryFirst(".o_actionswiper").scrollHeight).toBe(
        queryFirst(".target-component").scrollHeight,
        { message: "the swiper has the height of its content" }
    );
    expect(queryFirst(".o_actionswiper").scrollHeight).toBeGreaterThan(
        queryFirst(".o_actionswiper").clientHeight,
        { message: "the height of the swiper must make the parent div scrollable" }
    );
});

test("can perform actions by swiping to the right", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { ActionSwiper };
        static template = xml`
            <div class="d-flex">
                <ActionSwiper onRightSwipe = "{
                    action: () => this.onRightSwipe(),
                    icon: 'fa-circle',
                    bgColor: 'bg-warning'
                }">
                    <div class="target-component" style="width: 200px; height: 80px">Test</div>
                </ActionSwiper>
            </div>
        `;
        onRightSwipe() {
            expect.step("onRightSwipe");
        }
    }
    await mountWithCleanup(Parent);
    const swiper = queryFirst(".o_actionswiper");
    const targetContainer = queryFirst(".o_actionswiper_target_container");
    const dragHelper = await contains(swiper).drag({
        position: {
            clientX: 0,
            clientY: 0,
        },
    });
    await dragHelper.moveTo(swiper, {
        position: {
            clientX: (3 * swiper.clientWidth) / 4,
            clientY: 0,
        },
    });
    expect(targetContainer.style.transform).toInclude("translateX", {
        message: "target has translateX",
    });

    // Touch ends before the half of the distance has been reached
    await dragHelper.moveTo(swiper, {
        position: {
            clientX: swiper.clientWidth / 2 - 1,
            clientY: 0,
        },
    });
    await dragHelper.drop();
    await animationFrame();
    expect(targetContainer.style.transform).not.toInclude("translateX", {
        message: "target does not have a translate value",
    });

    // Touch ends once the half of the distance has been crossed
    await swipeRight(".o_actionswiper");
    // The action is performed AND the component is reset
    expect(targetContainer.style.transform).not.toInclude("translateX", {
        message: "target does not have a translate value",
    });

    expect.verifySteps(["onRightSwipe"]);
});

test("can perform actions by swiping in both directions", async () => {
    expect.assertions(5);
    class Parent extends Component {
        static props = ["*"];
        static components = { ActionSwiper };
        static template = xml`
                    <div class="d-flex">
                        <ActionSwiper
                            onRightSwipe = "{
                                action: () => this.onRightSwipe(),
                                icon: 'fa-circle',
                                bgColor: 'bg-warning'
                            }"
                            onLeftSwipe = "{
                                action: () => this.onLeftSwipe(),
                                icon: 'fa-check',
                                bgColor: 'bg-success'
                            }">
                                <div class="target-component" style="width: 250px; height: 80px">Swipe in both directions</div>
                        </ActionSwiper>
                    </div>
                `;
        onRightSwipe() {
            expect.step("onRightSwipe");
        }
        onLeftSwipe() {
            expect.step("onLeftSwipe");
        }
    }
    await mountWithCleanup(Parent);
    const swiper = queryFirst(".o_actionswiper");
    const targetContainer = queryFirst(".o_actionswiper_target_container");
    const dragHelper = await contains(swiper).drag({
        position: {
            clientX: 0,
            clientY: 0,
        },
    });
    await dragHelper.moveTo(swiper, {
        position: {
            clientX: (3 * swiper.clientWidth) / 4,
            clientY: 0,
        },
    });
    expect(targetContainer.style.transform).toInclude("translateX", {
        message: "target has translateX",
    });
    // Touch ends before the half of the distance has been reached to the left
    await dragHelper.moveTo(swiper, {
        position: {
            clientX: -swiper.clientWidth / 2 + 1,
            clientY: 0,
        },
    });

    await dragHelper.drop();

    expect(targetContainer.style.transform).not.toInclude("translateX", {
        message: "target does not have a translate value",
    });

    // Touch ends once the half of the distance has been crossed to the left
    await swipeLeft(".o_actionswiper");
    expect.verifySteps(["onLeftSwipe"]);
    // Touch ends once the half of the distance has been crossed to the right
    await swipeRight(".o_actionswiper");

    expect(targetContainer.style.transform).not.toInclude("translateX", {
        message: "target doesn't have translateX after all actions are performed",
    });

    expect.verifySteps(["onRightSwipe"]);
});

test("invert the direction of swipes when language is rtl", async () => {
    defineParams({
        lang_parameters: {
            direction: "rtl",
        },
    });
    class Parent extends Component {
        static props = ["*"];
        static components = { ActionSwiper };
        static template = xml`
                    <div class="d-flex">
                        <ActionSwiper
                            onRightSwipe = "{
                                action: () => this.onRightSwipe(),
                                icon: 'fa-circle',
                                bgColor: 'bg-warning'
                            }"
                            onLeftSwipe = "{
                                action: () => this.onLeftSwipe(),
                                icon: 'fa-check',
                                bgColor: 'bg-success'
                            }">
                                <div class="target-component" style="width: 250px; height: 80px">Swipe in both directions</div>
                        </ActionSwiper>
                    </div>
                `;
        onRightSwipe() {
            expect.step("onRightSwipe");
        }
        onLeftSwipe() {
            expect.step("onLeftSwipe");
        }
    }
    await mountWithCleanup(Parent);
    // Touch ends once the half of the distance has been crossed to the left
    await swipeLeft(".o_actionswiper");
    await advanceTime(500);
    // In rtl languages, actions are permuted
    expect.verifySteps(["onRightSwipe"]);
    await swipeRight(".o_actionswiper");
    await advanceTime(500);
    // In rtl languages, actions are permuted
    expect.verifySteps(["onLeftSwipe"]);
});

test("swiping when the swiper contains scrollable areas", async () => {
    expect.assertions(7);

    class Parent extends Component {
        static props = ["*"];
        static components = { ActionSwiper };
        static template = xml`
            <div class="d-flex">
                <ActionSwiper
                    onRightSwipe = "{
                        action: () => this.onRightSwipe(),
                        icon: 'fa-circle',
                        bgColor: 'bg-warning'
                    }"
                    onLeftSwipe = "{
                        action: () => this.onLeftSwipe(),
                        icon: 'fa-check',
                        bgColor: 'bg-success'
                    }">
                        <div class="target-component" style="width: 200px; height: 300px">
                            <h1>Test about swiping and scrolling</h1>
                            <div class="large-content overflow-auto">
                                <h2>This div contains a larger element that will make it scrollable</h2>
                                <p class="large-text" style="width: 400px">This element is so large it needs to be scrollable</p>
                            </div>
                        </div>
                </ActionSwiper>
            </div>
        `;

        onRightSwipe() {
            expect.step("onRightSwipe");
        }

        onLeftSwipe() {
            expect.step("onLeftSwipe");
        }
    }

    await mountWithCleanup(Parent);
    const swiper = queryFirst(".o_actionswiper");
    const targetContainer = queryFirst(".o_actionswiper_target_container");
    const scrollable = queryFirst(".large-content");
    const largeText = queryFirst(".large-text", { root: scrollable });
    const clientYMiddleScrollBar = Math.floor(
        scrollable.getBoundingClientRect().top + scrollable.getBoundingClientRect().height / 2
    );

    // The scrollable element is set as scrollable
    scrollable.scrollLeft = 100;
    let dragHelper = await contains(swiper).drag({
        position: {
            clientX: 0,
            clientY: 0,
        },
    });
    await dragHelper.moveTo(swiper, {
        position: {
            clientX: (3 * swiper.clientWidth) / 4,
            clientY: 0,
        },
    });
    expect(targetContainer.style.transform).toInclude("translateX", {
        message: "the swiper can swipe if the scrollable area is not under touch pressure",
    });
    await dragHelper.moveTo(swiper, {
        position: {
            clientX: 0,
            clientY: 0,
        },
    });
    await dragHelper.drop();

    dragHelper = await contains(largeText).drag({
        position: {
            clientX: scrollable.clientLeft,
            clientY: clientYMiddleScrollBar,
        },
    });
    await dragHelper.moveTo(largeText, {
        position: {
            clientX: scrollable.clientWidth,
            clientY: clientYMiddleScrollBar,
        },
    });
    expect(targetContainer.style.transform).not.toInclude("translateX", {
        message:
            "the swiper has not swiped to the right because the scrollable element was scrollable to the left",
    });
    await dragHelper.drop();
    // The scrollable element is set at its left limit
    scrollable.scrollLeft = 0;
    await hover(largeText, {
        position: {
            clientX: scrollable.clientLeft,
            clientY: clientYMiddleScrollBar,
        },
    });
    dragHelper = await contains(largeText).drag({
        position: {
            clientX: scrollable.clientLeft,
            clientY: clientYMiddleScrollBar,
        },
    });
    await dragHelper.moveTo(largeText, {
        position: {
            clientX: scrollable.clientWidth,
            clientY: clientYMiddleScrollBar,
        },
    });
    expect(targetContainer.style.transform).toInclude("translateX", {
        message:
            "the swiper has swiped to the right because the scrollable element couldn't scroll anymore to the left",
    });
    await dragHelper.drop();
    await advanceTime(500);
    expect.verifySteps(["onRightSwipe"]);

    dragHelper = await contains(largeText).drag({
        position: {
            clientX: scrollable.clientWidth,
            clientY: clientYMiddleScrollBar,
        },
    });
    await dragHelper.moveTo(largeText, {
        position: {
            clientX: scrollable.clientLeft,
            clientY: clientYMiddleScrollBar,
        },
    });
    expect(targetContainer.style.transform).not.toInclude("translateX", {
        message:
            "the swiper has not swiped to the left because the scrollable element was scrollable to the right",
    });
    await dragHelper.drop();

    // The scrollable element is set at its right limit
    scrollable.scrollLeft = scrollable.scrollWidth - scrollable.getBoundingClientRect().right;
    await hover(largeText, {
        position: {
            clientX: scrollable.clientWidth,
            clientY: clientYMiddleScrollBar,
        },
    });
    dragHelper = await contains(largeText).drag({
        position: {
            clientX: scrollable.clientWidth,
            clientY: clientYMiddleScrollBar,
        },
    });
    await dragHelper.moveTo(largeText, {
        position: {
            clientX: scrollable.clientLeft,
            clientY: clientYMiddleScrollBar,
        },
    });
    expect(targetContainer.style.transform).toInclude("translateX", {
        message:
            "the swiper has swiped to the left because the scrollable element couldn't scroll anymore to the right",
    });
    await dragHelper.drop();
    await advanceTime(500);
    expect.verifySteps(["onLeftSwipe"]);
});

test("preventing swipe on scrollable areas when language is rtl", async () => {
    expect.assertions(6);
    defineParams({
        lang_parameters: {
            direction: "rtl",
        },
    });

    class Parent extends Component {
        static props = ["*"];
        static components = { ActionSwiper };
        static template = xml`
            <div class="d-flex">
                <ActionSwiper
                    onRightSwipe="{
                        action: () => this.onRightSwipe(),
                        icon: 'fa-circle',
                        bgColor: 'bg-warning'
                    }"
                    onLeftSwipe="{
                        action: () => this.onLeftSwipe(),
                        icon: 'fa-check',
                        bgColor: 'bg-success'
                    }">
                        <div class="target-component" style="width: 200px; height: 300px">
                        <h1>Test about swiping and scrolling for rtl</h1>
                            <div class="large-content overflow-auto">
                                <h2>elballorcs ti ekam lliw taht tnemele regral a sniatnoc vid sihT</h2>
                                <p class="large-text" style="width: 400px">elballorcs eb ot sdeen ti egral os si tnemele sihT</p>
                            </div>
                        </div>
                </ActionSwiper>
            </div>
        `;

        onRightSwipe() {
            expect.step("onRightSwipe");
        }

        onLeftSwipe() {
            expect.step("onLeftSwipe");
        }
    }

    await mountWithCleanup(Parent);
    const targetContainer = queryFirst(".o_actionswiper_target_container");
    const scrollable = queryFirst(".large-content");
    const largeText = queryFirst(".large-text", { root: scrollable });
    const scrollableMiddleClientY = Math.floor(
        scrollable.getBoundingClientRect().top + scrollable.getBoundingClientRect().height / 2
    );
    // RIGHT => Left trigger
    // The scrollable element is set as scrollable
    scrollable.scrollLeft = 100;
    let dragHelper = await contains(largeText).drag({
        position: {
            clientX: scrollable.clientLeft,
            clientY: scrollableMiddleClientY,
        },
    });
    await dragHelper.moveTo(largeText, {
        position: {
            clientX: scrollable.clientWidth,
            clientY: scrollableMiddleClientY,
        },
    });

    expect(targetContainer.style.transform).not.toInclude("translateX", {
        message:
            "the swiper has not swiped to the right because the scrollable element was scrollable to the left",
    });
    await dragHelper.drop();

    // The scrollable element is set at its left limit
    scrollable.scrollLeft = 0;
    await hover(largeText, {
        position: {
            clientX: scrollable.clientLeft,
            clientY: scrollableMiddleClientY,
        },
    });
    dragHelper = await contains(largeText).drag({
        position: {
            clientX: scrollable.clientLeft,
            clientY: scrollableMiddleClientY,
        },
    });
    await dragHelper.moveTo(largeText, {
        position: {
            clientX: scrollable.clientWidth,
            clientY: scrollableMiddleClientY,
        },
    });
    expect(targetContainer.style.transform).toInclude("translateX", {
        message:
            "the swiper has swiped to the right because the scrollable element couldn't scroll anymore to the left",
    });
    await dragHelper.drop();
    await advanceTime(500);
    // In rtl languages, actions are permuted
    expect.verifySteps(["onLeftSwipe"]);
    // LEFT => RIGHT trigger
    await hover(largeText, {
        position: {
            clientX: scrollable.clientWidth,
            clientY: scrollableMiddleClientY,
        },
    });
    dragHelper = await contains(largeText).drag({
        position: {
            clientX: scrollable.clientWidth,
            clientY: scrollableMiddleClientY,
        },
    });
    await dragHelper.moveTo(largeText, {
        position: {
            clientX: scrollable.clientLeft,
            clientY: scrollableMiddleClientY,
        },
    });
    expect(targetContainer.style.transform).not.toInclude("translateX", {
        message:
            "the swiper has not swiped to the left because the scrollable element was scrollable to the right",
    });
    await dragHelper.drop();
    // The scrollable element is set at its right limit
    scrollable.scrollLeft = scrollable.scrollWidth - scrollable.getBoundingClientRect().right;
    await hover(largeText, {
        position: {
            clientX: scrollable.clientWidth,
            clientY: scrollableMiddleClientY,
        },
    });
    dragHelper = await contains(largeText).drag({
        position: {
            clientX: scrollable.clientWidth,
            clientY: scrollableMiddleClientY,
        },
    });
    await dragHelper.moveTo(largeText, {
        position: {
            clientX: scrollable.clientLeft,
            clientY: scrollableMiddleClientY,
        },
    });
    expect(targetContainer.style.transform).toInclude("translateX", {
        message:
            "the swiper has swiped to the left because the scrollable element couldn't scroll anymore to the right",
    });
    await dragHelper.drop();
    await advanceTime(500);

    // In rtl languages, actions are permuted
    expect.verifySteps(["onRightSwipe"]);
});

test("swipeInvalid prop prevents swiping", async () => {
    expect.assertions(2);

    class Parent extends Component {
        static props = ["*"];
        static components = { ActionSwiper };
        static template = xml`
                <div class="d-flex">
                    <ActionSwiper onRightSwipe = "{
                        action: () => this.onRightSwipe(),
                        icon: 'fa-circle',
                        bgColor: 'bg-warning',
                    }" swipeInvalid = "swipeInvalid">
                        <div class="target-component" style="width: 200px; height: 80px">Test</div>
                    </ActionSwiper>
                </div>
            `;
        onRightSwipe() {
            expect.step("onRightSwipe");
        }
        swipeInvalid() {
            expect.step("swipeInvalid");
            return true;
        }
    }
    await mountWithCleanup(Parent);
    const targetContainer = queryFirst(".o_actionswiper_target_container");
    // Touch ends once the half of the distance has been crossed
    await swipeRight(".o_actionswiper");

    expect(targetContainer.style.transform).not.toInclude("translateX", {
        message: "target doesn't have translateX after action is performed",
    });
    expect.verifySteps(["swipeInvalid"]);
});

test("action should be done before a new render", async () => {
    let executingAction = false;
    const prom = new Deferred();

    patchWithCleanup(ActionSwiper.prototype, {
        setup() {
            super.setup();
            onPatched(() => {
                if (executingAction) {
                    expect.step("ActionSwiper patched");
                }
            });
        },
    });

    class Parent extends Component {
        static props = [];
        static components = { ActionSwiper };
        static template = xml`
                <div class="d-flex">
                   <ActionSwiper animationType="'forwards'" onRightSwipe = "{
                       action: () => this.onRightSwipe(),
                       icon: 'fa-circle',
                       bgColor: 'bg-warning',
                   }">
                       <span>test</span>
                   </ActionSwiper>
               </div>
            `;

        async onRightSwipe() {
            await animationFrame();
            expect.step("action done");
            prom.resolve();
        }
    }

    await mountWithCleanup(Parent);
    await swipeRight(".o_actionswiper");
    executingAction = true;
    await prom;
    await animationFrame();
    expect.verifySteps(["action done", "ActionSwiper patched"]);
});
