/** @odoo-module **/

import { ActionSwiper } from "@web/core/action_swiper/action_swiper";
import { registry } from "@web/core/registry";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";

import {
    mount,
    nextTick,
    triggerEvent,
    getFixture,
    mockTimeout,
} from "@web/../tests/helpers/utils";

import { Component, xml } from "@odoo/owl";
const serviceRegistry = registry.category("services");

let env;
let target;

QUnit.module("ActionSwiper", ({ beforeEach }) => {
    beforeEach(async () => {
        env = await makeTestEnv();
        target = getFixture();
    });

    // Tests marked as [REQUIRE TOUCHEVENT] will fail on browsers that don't support
    // TouchEvent by default. It might be an option to activate on some browser.

    QUnit.test("render only its target if no props is given", async (assert) => {
        class Parent extends Component {}
        Parent.components = { ActionSwiper };
        Parent.template = xml`
            <div class="d-flex">
                <ActionSwiper>
                    <div class="target-component"/>
                </ActionSwiper>
            </div>
        `;
        await mount(Parent, target, { env });
        assert.containsNone(target, "div.o_actionswiper");
        assert.containsOnce(target, "div.target-component");
    });

    QUnit.test("only render the necessary divs", async (assert) => {
        await mount(ActionSwiper, target, {
            env,
            props: {
                onRightSwipe: {
                    action: () => {},
                    icon: "fa-circle",
                    bgColor: "bg-warning",
                },
                slots: {},
            },
        });
        assert.containsOnce(target, "div.o_actionswiper_right_swipe_area");
        assert.containsNone(target, "div.o_actionswiper_left_swipe_area");
        await mount(ActionSwiper, target, {
            env,
            props: {
                onLeftSwipe: {
                    action: () => {},
                    icon: "fa-circle",
                    bgColor: "bg-warning",
                },
                slots: {},
            },
        });
        assert.containsOnce(target, "div.o_actionswiper_right_swipe_area");
        assert.containsOnce(target, "div.o_actionswiper_left_swipe_area");
    });

    QUnit.test("render with the height of its content", async (assert) => {
        assert.expect(2);
        class Parent extends Component {
            onRightSwipe() {
                assert.step("onRightSwipe");
            }
        }
        Parent.components = { ActionSwiper };
        Parent.template = xml`
            <div class="o-container d-flex" style="width: 200px; height: 200px; overflow: auto">
                <ActionSwiper onRightSwipe = "{
                    action: onRightSwipe,
                    icon: 'fa-circle',
                    bgColor: 'bg-warning'
                }">
                    <div class="target-component" style="height: 800px">This element is very high and
                    the o-container element must have a scrollbar</div>
                </ActionSwiper>
            </div>
        `;
        await mount(Parent, target, { env });
        assert.ok(
            target.querySelector(".o_actionswiper").scrollHeight ===
                target.querySelector(".target-component").scrollHeight,
            "the swiper has the height of its content"
        );
        assert.ok(
            target.querySelector(".o_actionswiper").scrollHeight >
                target.querySelector(".o_actionswiper").clientHeight,
            "the height of the swiper must make the parent div scrollable"
        );
    });

    QUnit.test(
        "can perform actions by swiping to the right [REQUIRE TOUCHEVENT]",
        async (assert) => {
            assert.expect(5);
            const { execRegisteredTimeouts } = mockTimeout();
            class Parent extends Component {
                onRightSwipe() {
                    assert.step("onRightSwipe");
                }
            }
            Parent.components = { ActionSwiper };
            Parent.template = xml`
                <div class="d-flex">
                    <ActionSwiper onRightSwipe = "{
                        action: onRightSwipe,
                        icon: 'fa-circle',
                        bgColor: 'bg-warning'
                    }">
                        <div class="target-component" style="width: 200px; height: 80px">Test</div>
                    </ActionSwiper>
                </div>
            `;
            await mount(Parent, target, { env });
            const swiper = target.querySelector(".o_actionswiper");
            const targetContainer = target.querySelector(".o_actionswiper_target_container");
            await triggerEvent(target, ".o_actionswiper", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: 0,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: (3 * swiper.clientWidth) / 4,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            assert.ok(
                targetContainer.style.transform.includes("translateX"),
                "target has translateX"
            );
            // Touch ends before the half of the distance has been reached
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: swiper.clientWidth / 2 - 1,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            execRegisteredTimeouts();
            await nextTick();
            assert.ok(
                !targetContainer.style.transform.includes("translateX"),
                "target does not have a translate value"
            );
            // Touch ends once the half of the distance has been crossed
            await triggerEvent(target, ".o_actionswiper", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: swiper.clientWidth / 2,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: swiper.clientWidth + 1,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            execRegisteredTimeouts();
            await nextTick();
            // The action is performed AND the component is reset
            assert.ok(
                !targetContainer.style.transform.includes("translateX"),
                "target doesn't have translateX after action is performed"
            );
            assert.verifySteps(["onRightSwipe"]);
        }
    );

    QUnit.test(
        "can perform actions by swiping in both directions [REQUIRE TOUCHEVENT]",
        async (assert) => {
            assert.expect(7);
            const { execRegisteredTimeouts } = mockTimeout();
            class Parent extends Component {
                onRightSwipe() {
                    assert.step("onRightSwipe");
                }
                onLeftSwipe() {
                    assert.step("onLeftSwipe");
                }
            }
            Parent.components = { ActionSwiper };
            Parent.template = xml`
                <div class="d-flex">
                    <ActionSwiper 
                        onRightSwipe = "{
                            action: onRightSwipe,
                            icon: 'fa-circle',
                            bgColor: 'bg-warning'
                        }"
                        onLeftSwipe = "{
                            action: onLeftSwipe,
                            icon: 'fa-check',
                            bgColor: 'bg-success'
                        }">
                            <div class="target-component" style="width: 250px; height: 80px">Swipe in both directions</div>
                    </ActionSwiper>
                </div>
            `;
            await mount(Parent, target, { env });
            const swiper = target.querySelector(".o_actionswiper");
            const targetContainer = target.querySelector(".o_actionswiper_target_container");
            await triggerEvent(target, ".o_actionswiper", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: 0,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: (3 * swiper.clientWidth) / 4,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            assert.ok(
                targetContainer.style.transform.includes("translateX"),
                "target has translateX"
            );
            // Touch ends before the half of the distance has been reached to the left
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: -swiper.clientWidth / 2 + 1,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            execRegisteredTimeouts();
            await nextTick();
            assert.ok(
                !targetContainer.style.transform.includes("translateX"),
                "target does not have a translate value"
            );
            // Touch ends once the half of the distance has been crossed to the left
            await triggerEvent(target, ".o_actionswiper", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: swiper.clientWidth / 2,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: -swiper.clientWidth - 1,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            execRegisteredTimeouts();
            await nextTick();
            assert.verifySteps(["onLeftSwipe"], "the onLeftSwipe props action has been performed");
            // Touch ends once the half of the distance has been crossed to the right
            await triggerEvent(target, ".o_actionswiper", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: swiper.clientWidth / 2,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: swiper.clientWidth + 1,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            execRegisteredTimeouts();
            await nextTick();
            assert.ok(
                !targetContainer.style.transform.includes("translateX"),
                "target doesn't have translateX after all actions are performed"
            );
            assert.verifySteps(
                ["onRightSwipe"],
                "the onRightSwipe props action has been performed"
            );
        }
    );

    QUnit.test(
        "invert the direction of swipes when language is rtl [REQUIRE TOUCHEVENT]",
        async (assert) => {
            assert.expect(7);
            const { execRegisteredTimeouts } = mockTimeout();
            class Parent extends Component {
                onRightSwipe() {
                    assert.step("onRightSwipe");
                }
                onLeftSwipe() {
                    assert.step("onLeftSwipe");
                }
            }
            Parent.components = { ActionSwiper };
            Parent.template = xml`
                <div class="d-flex">
                    <ActionSwiper 
                        onRightSwipe = "{
                            action: onRightSwipe,
                            icon: 'fa-circle',
                            bgColor: 'bg-warning'
                        }"
                        onLeftSwipe = "{
                            action: onLeftSwipe,
                            icon: 'fa-check',
                            bgColor: 'bg-success'
                        }">
                            <div class="target-component" style="width: 250px; height: 80px">Swipe in both directions</div>
                    </ActionSwiper>
                </div>
            `;
            serviceRegistry.add("localization", makeFakeLocalizationService({ direction: "rtl" }));
            await mount(Parent, target, { env });
            const swiper = target.querySelector(".o_actionswiper");
            const targetContainer = target.querySelector(".o_actionswiper_target_container");
            await triggerEvent(target, ".o_actionswiper", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: 0,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: (3 * swiper.clientWidth) / 4,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            assert.ok(
                targetContainer.style.transform.includes("translateX"),
                "target has translateX"
            );
            // Touch ends before the half of the distance has been reached to the left
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: -swiper.clientWidth / 2 + 1,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            execRegisteredTimeouts();
            await nextTick();
            assert.ok(
                !targetContainer.style.transform.includes("translateX"),
                "target does not have a translate value"
            );
            // Touch ends once the half of the distance has been crossed to the left
            await triggerEvent(target, ".o_actionswiper", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: swiper.clientWidth / 2,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: -swiper.clientWidth - 1,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            execRegisteredTimeouts();
            await nextTick();
            // In rtl languages, actions are permuted
            assert.verifySteps(
                ["onRightSwipe"],
                "the onRightSwipe props action has been performed"
            );
            await triggerEvent(target, ".o_actionswiper", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: swiper.clientWidth / 2,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: swiper.clientWidth + 1,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            execRegisteredTimeouts();
            await nextTick();
            assert.ok(
                !targetContainer.style.transform.includes("translateX"),
                "target doesn't have translateX after all actions are performed"
            );
            // In rtl languages, actions are permuted
            assert.verifySteps(["onLeftSwipe"], "the onLeftSwipe props action has been performed");
        }
    );

    QUnit.test(
        "swiping when the swiper contains scrollable areas [REQUIRE TOUCHEVENT]",
        async (assert) => {
            assert.expect(9);
            const { execRegisteredTimeouts } = mockTimeout();
            class Parent extends Component {
                onRightSwipe() {
                    assert.step("onRightSwipe");
                }
                onLeftSwipe() {
                    assert.step("onLeftSwipe");
                }
            }
            Parent.components = { ActionSwiper };
            Parent.template = xml`
                <div class="d-flex">
                    <ActionSwiper 
                        onRightSwipe = "{
                            action: onRightSwipe,
                            icon: 'fa-circle',
                            bgColor: 'bg-warning'
                        }"
                        onLeftSwipe = "{
                            action: onLeftSwipe,
                            icon: 'fa-check',
                            bgColor: 'bg-success'
                        }">
                            <div class="target-component" style="width: 200px; height: 300px">
                            <h1>Test about swiping and scrolling</h1>
                                <div class="large-content" style="overflow: auto">
                                    <h2>This div contains a larger element that will make it scrollable</h2>
                                    <p class="large-text" style="width: 400px">This element is so large it needs to be scrollable</p>
                                </div>
                            </div>
                    </ActionSwiper>
                </div>
            `;
            await mount(Parent, target, { env });
            const swiper = target.querySelector(".o_actionswiper");
            const targetContainer = target.querySelector(".o_actionswiper_target_container");
            const scrollable = target.querySelector(".large-content");
            // The scrollable element is set as scrollable
            scrollable.scrollLeft = 100;
            await triggerEvent(target, ".o_actionswiper", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: 0,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: (3 * swiper.clientWidth) / 4,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            assert.ok(
                targetContainer.style.transform.includes("translateX"),
                "the swiper can swipe if the scrollable area is not under touch pressure"
            );
            await triggerEvent(target, ".o_actionswiper", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: 0,
                        clientY: 0,
                        target: target,
                    },
                ],
            });
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            await triggerEvent(scrollable, ".large-text", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientLeft,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            await triggerEvent(scrollable, ".large-text", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientWidth,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            assert.ok(
                !targetContainer.style.transform.includes("translateX"),
                "the swiper has not swiped to the right because the scrollable element was scrollable to the left"
            );
            // The scrollable element is set at its left limit
            scrollable.scrollLeft = 0;
            await triggerEvent(scrollable, ".large-text", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientLeft,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            await triggerEvent(scrollable, ".large-text", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientWidth,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            assert.ok(
                targetContainer.style.transform.includes("translateX"),
                "the swiper has swiped to the right because the scrollable element couldn't scroll anymore to the left"
            );
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            execRegisteredTimeouts();
            await nextTick();
            assert.verifySteps(
                ["onRightSwipe"],
                "the onRightSwipe props action has been performed"
            );
            await triggerEvent(scrollable, ".large-text", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientWidth,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            await triggerEvent(scrollable, ".large-text", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientLeft,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            assert.ok(
                !targetContainer.style.transform.includes("translateX"),
                "the swiper has not swiped to the left because the scrollable element was scrollable to the right"
            );
            // The scrollable element is set at its right limit
            scrollable.scrollLeft =
                scrollable.scrollWidth - scrollable.getBoundingClientRect().right;
            await triggerEvent(scrollable, ".large-text", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientWidth,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            await triggerEvent(scrollable, ".large-text", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientLeft,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            assert.ok(
                targetContainer.style.transform.includes("translateX"),
                "the swiper has swiped to the left because the scrollable element couldn't scroll anymore to the right"
            );
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            execRegisteredTimeouts();
            await nextTick();
            assert.verifySteps(["onLeftSwipe"], "the onLeftSwipe props action has been performed");
        }
    );

    QUnit.test(
        "preventing swipe on scrollable areas when language is rtl [REQUIRE TOUCHEVENT]",
        async (assert) => {
            assert.expect(8);
            const { execRegisteredTimeouts } = mockTimeout();
            class Parent extends Component {
                onRightSwipe() {
                    assert.step("onRightSwipe");
                }
                onLeftSwipe() {
                    assert.step("onLeftSwipe");
                }
            }
            Parent.components = { ActionSwiper };
            Parent.template = xml`
                <div class="d-flex">
                    <ActionSwiper
                        onRightSwipe = "{
                            action: onRightSwipe,
                            icon: 'fa-circle',
                            bgColor: 'bg-warning'
                        }"
                        onLeftSwipe = "{
                            action: onLeftSwipe,
                            icon: 'fa-check',
                            bgColor: 'bg-success'
                        }">
                            <div class="target-component" style="width: 200px; height: 300px">
                            <h1>Test about swiping and scrolling for rtl</h1>
                                <div class="large-content" style="overflow: auto">
                                    <h2>elballorcs ti ekam lliw taht tnemele regral a sniatnoc vid sihT</h2>
                                    <p class="large-text" style="width: 400px">elballorcs eb ot sdeen ti egral os si tnemele sihT</p>
                                </div>
                            </div>
                    </ActionSwiper>
                </div>
            `;
            serviceRegistry.add("localization", makeFakeLocalizationService({ direction: "rtl" }));
            await mount(Parent, target, { env });
            const targetContainer = target.querySelector(".o_actionswiper_target_container");
            const scrollable = target.querySelector(".large-content");
            // The scrollable element is set as scrollable
            scrollable.scrollLeft = 100;
            await triggerEvent(scrollable, ".large-text", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientLeft,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            await triggerEvent(scrollable, ".large-text", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientWidth,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            assert.ok(
                !targetContainer.style.transform.includes("translateX"),
                "the swiper has not swiped to the right because the scrollable element was scrollable to the left"
            );
            // The scrollable element is set at its left limit
            scrollable.scrollLeft = 0;
            await triggerEvent(scrollable, ".large-text", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientLeft,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            await triggerEvent(scrollable, ".large-text", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientWidth,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            assert.ok(
                targetContainer.style.transform.includes("translateX"),
                "the swiper has swiped to the right because the scrollable element couldn't scroll anymore to the left"
            );
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            execRegisteredTimeouts();
            await nextTick();
            // In rtl languages, actions are permuted
            assert.verifySteps(["onLeftSwipe"], "the onLeftSwipe props action has been performed");
            await triggerEvent(scrollable, ".large-text", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientWidth,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            await triggerEvent(scrollable, ".large-text", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientLeft,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            assert.ok(
                !targetContainer.style.transform.includes("translateX"),
                "the swiper has not swiped to the left because the scrollable element was scrollable to the right"
            );
            // The scrollable element is set at its right limit
            scrollable.scrollLeft =
                scrollable.scrollWidth - scrollable.getBoundingClientRect().right;
            await triggerEvent(scrollable, ".large-text", "touchstart", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientWidth,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            await triggerEvent(scrollable, ".large-text", "touchmove", {
                touches: [
                    {
                        identifier: 0,
                        clientX: scrollable.clientLeft,
                        clientY:
                            scrollable.getBoundingClientRect().top +
                            scrollable.getBoundingClientRect().height / 2,
                        target: scrollable.querySelector(".large-text"),
                    },
                ],
            });
            assert.ok(
                targetContainer.style.transform.includes("translateX"),
                "the swiper has swiped to the left because the scrollable element couldn't scroll anymore to the right"
            );
            await triggerEvent(target, ".o_actionswiper", "touchend", {});
            execRegisteredTimeouts();
            await nextTick();
            // In rtl languages, actions are permuted
            assert.verifySteps(
                ["onRightSwipe"],
                "the onRightSwipe props action has been performed"
            );
        }
    );

    QUnit.test("swipeInvalid prop prevents swiping", async (assert) => {
        assert.expect(3);
        const { execRegisteredTimeouts } = mockTimeout();
        class Parent extends Component {
            onRightSwipe() {
                assert.step("onRightSwipe");
            }
            swipeInvalid() {
                assert.step("swipeInvalid");
                return true;
            }
        }
        Parent.components = { ActionSwiper };
        Parent.template = xml`
            <div class="d-flex">
                <ActionSwiper onRightSwipe = "{
                    action: onRightSwipe,
                    icon: 'fa-circle',
                    bgColor: 'bg-warning',
                }" swipeInvalid = "swipeInvalid">
                    <div class="target-component" style="width: 200px; height: 80px">Test</div>
                </ActionSwiper>
            </div>
        `;
        await mount(Parent, target, { env });
        const swiper = target.querySelector(".o_actionswiper");
        const targetContainer = target.querySelector(".o_actionswiper_target_container");
        // Touch ends once the half of the distance has been crossed
        await triggerEvent(target, ".o_actionswiper", "touchstart", {
            touches: [
                {
                    identifier: 0,
                    clientX: swiper.clientWidth / 2,
                    clientY: 0,
                    target: target,
                },
            ],
        });
        await triggerEvent(target, ".o_actionswiper", "touchmove", {
            touches: [
                {
                    identifier: 0,
                    clientX: swiper.clientWidth + 1,
                    clientY: 0,
                    target: target,
                },
            ],
        });
        await triggerEvent(target, ".o_actionswiper", "touchend", {});
        execRegisteredTimeouts();
        await nextTick();
        assert.ok(
            !targetContainer.style.transform.includes("translateX"),
            "target doesn't have translateX after action is performed"
        );
        assert.verifySteps(["swipeInvalid"]);
    });
});
