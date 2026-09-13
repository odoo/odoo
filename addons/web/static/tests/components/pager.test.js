// @ts-check

import { expect, test } from "@odoo/hoot";
import { click, press, queryOne } from "@odoo/hoot-dom";
import { animationFrame, Deferred, runAllTimers } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    contains,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { Pager } from "@web/components/pager/pager";
import { config as transitionConfig } from "@web/core/transition";

class PagerController extends Component {
    static template = xml`<Pager t-props="state" />`;
    static components = { Pager };
    static props = ["*"];
    setup() {
        this.state = useState({ ...this.props });
    }
    async updateProps(nextProps) {
        Object.assign(this.state, nextProps);
        await animationFrame();
    }
}

test("basic interactions", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            async onUpdate(data) {
                expect.step(`offset: ${data.offset}, limit: ${data.limit}`);
                await pager.updateProps(data);
            },
        },
    });

    await contains(".o_pager button.o_pager_next:enabled").click();
    await contains(".o_pager button.o_pager_previous:enabled").click();

    expect.verifySteps(["offset: 4, limit: 4", "offset: 0, limit: 4"]);
});

test.tags("desktop");
test("basic interactions on desktop", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            async onUpdate(data) {
                await pager.updateProps(data);
            },
        },
    });

    expect(".o_pager_counter .o_pager_value").toHaveText("1-4");

    await click(".o_pager button.o_pager_next");
    await animationFrame();

    expect(".o_pager_counter .o_pager_value").toHaveText("5-8");
});

test.tags("mobile");
test("basic interactions on mobile", async () => {
    patchWithCleanup(transitionConfig, { disabled: true });
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            async onUpdate(data) {
                await pager.updateProps(data);
            },
        },
    });

    expect(".o_pager_indicator").toHaveCount(0);

    await click(".o_pager button.o_pager_next");
    await animationFrame();
    await animationFrame();

    expect(".o_pager_indicator").toHaveCount(1);
    expect(".o_pager_indicator .o_pager_value").toHaveText("5-8");
    await runAllTimers();
    await animationFrame();

    expect(".o_pager_indicator").toHaveCount(0);

    await click(".o_pager button.o_pager_previous");
    await animationFrame();
    await animationFrame();

    expect(".o_pager_indicator").toHaveCount(1);
    expect(".o_pager_indicator .o_pager_value").toHaveText("1-4");
    await runAllTimers();
    await animationFrame();

    expect(".o_pager_indicator").toHaveCount(0);
});

test.tags("desktop");
test("edit the pager", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            async onUpdate(data) {
                await pager.updateProps(data);
            },
        },
    });

    await click(".o_pager_value");
    await animationFrame();

    expect("input").toHaveCount(1);
    expect(".o_pager_counter .o_pager_value").toHaveValue("1-4");

    await contains("input.o_pager_value").edit("1-6");
    await click(document.body);
    await animationFrame();
    await animationFrame();

    expect("input").toHaveCount(0);
    expect(".o_pager_counter .o_pager_value").toHaveText("1-6");
});

test.tags("desktop");
test("keydown on pager with same value", async () => {
    await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            onUpdate(data) {
                expect.step("pager-changed");
            },
        },
    });

    await click(".o_pager_value");
    await animationFrame();

    expect("input").toHaveCount(1);
    expect(".o_pager_counter .o_pager_value").toHaveValue("1-4");
    expect.verifySteps([]);

    await press("Enter");
    await animationFrame();
    expect("input").toHaveCount(0);
    expect(".o_pager_counter .o_pager_value").toHaveText("1-4");
    expect.verifySteps(["pager-changed"]);
});

test.tags("desktop");
test("pager value formatting", async () => {
    expect.assertions(8);
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            async onUpdate(data) {
                await pager.updateProps(data);
            },
        },
    });

    expect(".o_pager_counter .o_pager_value").toHaveText("1-4");

    async function inputAndAssert(inputValue, expected) {
        await click(".o_pager_counter .o_pager_value");
        await animationFrame();
        await contains("input.o_pager_value").edit(inputValue);
        await click(document.body);
        await animationFrame();
        await animationFrame();
        expect(".o_pager_counter .o_pager_value").toHaveText(expected);
    }

    await inputAndAssert("4-4", "4");
    await inputAndAssert("1-11", "1-10");
    await inputAndAssert("20-15", "10");
    await inputAndAssert("6-5", "10");
    await inputAndAssert("definitelyValidNumber", "10");
    await inputAndAssert(" 1 ,  2   ", "1-2");
    await inputAndAssert("3  8", "3-8");
});

test("pager disabling", async () => {
    const reloadPromise = new Deferred();
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            async onUpdate(data) {
                await reloadPromise;
                await pager.updateProps(data);
            },
        },
    });

    await click(".o_pager button.o_pager_next");
    await animationFrame();
    expect(".o_pager button.o_pager_next").toHaveAttribute("disabled");

    await click(".o_pager button.o_pager_previous");
    await animationFrame();
    expect(".o_pager button.o_pager_previous").toHaveAttribute("disabled");
});

test.tags("desktop");
test("pager disabling on desktop", async () => {
    const reloadPromise = new Deferred();
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            async onUpdate(data) {
                await reloadPromise;
                await pager.updateProps(data);
            },
        },
    });

    await click(".o_pager button.o_pager_next");
    await animationFrame();
    await click(".o_pager_value");
    await animationFrame();

    expect("button").toHaveCount(2);
    expect("button:nth-child(1)").toHaveAttribute("disabled");
    expect("button:nth-child(2)").toHaveAttribute("disabled");
    expect("span.o_pager_value").toHaveCount(1);

    reloadPromise.resolve();
    await animationFrame();
    await animationFrame();

    expect("button").toHaveCount(2);
    expect("button:nth-child(1)").not.toHaveAttribute("disabled");
    expect("button:nth-child(2)").not.toHaveAttribute("disabled");
    expect(".o_pager_counter .o_pager_value").toHaveText("5-8");

    await click(".o_pager_value");
    await animationFrame();

    expect("input.o_pager_value").toHaveCount(1);
});

test.tags("desktop");
test("desktop input interaction", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            async onUpdate(data) {
                await pager.updateProps(data);
            },
        },
    });
    await click(".o_pager_value");
    await animationFrame();

    expect("input").toHaveCount(1);
    expect("input").toBeFocused();
    await click(document.body);
    await animationFrame();
    await animationFrame();
    expect("input").toHaveCount(0);
});

test.tags("desktop");
test("updateTotal props: click on total", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: 10,
            onUpdate() {},
            async updateTotal() {
                await pager.updateProps({ total: 25, updateTotal: undefined });
            },
        },
    });

    expect(".o_pager_value").toHaveText("1-5");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    await click(".o_pager_limit_fetch");
    await animationFrame();
    expect(".o_pager_value").toHaveText("1-5");
    expect(".o_pager_limit").toHaveText("25");
    expect(".o_pager_limit").not.toHaveClass("o_pager_limit_fetch");
});

test.tags("desktop");
test("updateTotal props: click next", async () => {
    let tempTotal = 10;
    const realTotal = 18;
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: tempTotal,
            async onUpdate(data) {
                tempTotal = Math.min(
                    realTotal,
                    Math.max(tempTotal, data.offset + data.limit),
                );
                const nextProps = { ...data, total: tempTotal };
                if (tempTotal === realTotal) {
                    nextProps.updateTotal = undefined;
                }
                await pager.updateProps(nextProps);
            },
            updateTotal() {},
        },
    });

    expect(".o_pager_value").toHaveText("1-5");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    await contains(".o_pager_next:enabled").click();

    expect(".o_pager_value").toHaveText("6-10");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    await contains(".o_pager_next:enabled").click();

    expect(".o_pager_value").toHaveText("11-15");
    expect(".o_pager_limit").toHaveText("15+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    await contains(".o_pager_next:enabled").click();

    expect(".o_pager_value").toHaveText("16-18");
    expect(".o_pager_limit").toHaveText("18");
    expect(".o_pager_limit").not.toHaveClass("o_pager_limit_fetch");
});

test.tags("desktop");
test("updateTotal props: edit input", async () => {
    let tempTotal = 10;
    const realTotal = 18;
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: tempTotal,
            async onUpdate(data) {
                tempTotal = Math.min(
                    realTotal,
                    Math.max(tempTotal, data.offset + data.limit),
                );
                const nextProps = { ...data, total: tempTotal };
                if (tempTotal === realTotal) {
                    nextProps.updateTotal = undefined;
                }
                await pager.updateProps(nextProps);
            },
            updateTotal() {},
        },
    });

    expect(".o_pager_value").toHaveText("1-5");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    await click(".o_pager_value");
    await animationFrame();
    await contains("input.o_pager_value").edit("3-8");
    await click(document.body);
    await animationFrame();
    await animationFrame();

    expect(".o_pager_value").toHaveText("3-8");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    await click(".o_pager_value");
    await animationFrame();
    await contains("input.o_pager_value").edit("3-20");
    await click(document.body);
    await animationFrame();
    await animationFrame();
    expect(".o_pager_value").toHaveText("3-18");
    expect(".o_pager_limit").toHaveText("18");
    expect(".o_pager_limit").not.toHaveClass("o_pager_limit_fetch");
});

test.tags("desktop");
test("updateTotal props: can use next even if single page", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: 5,
            async onUpdate(data) {
                await pager.updateProps({ ...data, total: 10 });
            },
            updateTotal() {},
        },
    });

    expect(".o_pager_value").toHaveText("1-5");
    expect(".o_pager_limit").toHaveText("5+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    await click(".o_pager_next");
    await animationFrame();

    expect(".o_pager_value").toHaveText("6-10");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");
});

test.tags("desktop");
test("updateTotal props: a rejected count re-enables the pager", async () => {
    expect.errors(1);
    const def = new Deferred();
    await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: 10,
            onUpdate() {},
            async updateTotal() {
                await def;
                throw new Error("count failed");
            },
        },
    });

    expect(".o_pager_limit").toHaveText("10+");

    await click(".o_pager_limit_fetch");
    await animationFrame();
    expect(".o_pager button.o_pager_next").toHaveAttribute("disabled");

    def.resolve();
    await animationFrame();
    await animationFrame();

    expect(".o_pager button.o_pager_next").not.toHaveAttribute("disabled");
    expect.verifyErrors(["count failed"]);
});

test.tags("desktop");
test("updateTotal props: click previous", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: 10,
            async onUpdate(data) {
                await pager.updateProps(data);
            },
            async updateTotal() {
                const total = 23;
                await pager.updateProps({ total, updateTotal: undefined });
                return total;
            },
        },
    });

    expect(".o_pager_value").toHaveText("1-5");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    await click(".o_pager_previous");
    await animationFrame();
    await animationFrame();

    expect(".o_pager_value").toHaveText("21-23");
    expect(".o_pager_limit").toHaveText("23");
    expect(".o_pager_limit").not.toHaveClass("o_pager_limit_fetch");
});

test("parse returns a plain object, not a promise", async () => {
    let pager;
    patchWithCleanup(Pager.prototype, {
        setup() {
            super.setup();
            pager = this;
        },
    });
    await mountWithCleanup(PagerController, {
        props: { offset: 0, limit: 10, total: 50, onUpdate: () => {} },
    });
    const parsed = /** @type {any} */ (pager).parse("2-4");
    expect(parsed instanceof Promise).toBe(false);
    expect(parsed).toEqual({ minimum: 1, maximum: 4 });
});

test.tags("desktop");
test("previous does not resolve the total twice on a double click", async () => {
    const def = new Deferred();
    await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: 10,
            onUpdate() {
                expect.step("update");
            },
            async updateTotal() {
                expect.step("updateTotal");
                await def;
                return 18;
            },
        },
    });

    await click(".o_pager_previous");
    await click(".o_pager_previous");
    expect.verifySteps(["updateTotal"]);

    def.resolve(18);
    await animationFrame();
    expect.verifySteps(["update"]);
});

test.tags("desktop");
test("a rejected pager entry is put back, not left in the input", async () => {
    await mountWithCleanup(PagerController, {
        props: { offset: 0, limit: 10, total: 50, onUpdate: () => {} },
    });

    expect(".o_pager_value").toHaveText("1-10");

    await contains(".o_pager_value").click();
    await contains("input.o_pager_value").edit("abc", { confirm: false });
    await press("Enter");
    await animationFrame();

    expect(".o_pager_value").toHaveValue("1-10", {
        message: "an unparseable entry reverts to the current range",
    });

    await contains("input.o_pager_value").edit("8-2", { confirm: false });
    await press("Enter");
    await animationFrame();

    expect(".o_pager_value").toHaveValue("1-10", {
        message: "a backwards range reverts too",
    });
});

test.tags("desktop");
test("editing survives a pointerdown inside the input, and only that", async () => {
    class Host extends Component {
        static template = xml`<div><span class="outside">elsewhere</span><Pager t-props="state"/></div>`;
        static components = { Pager };
        static props = ["*"];
        setup() {
            this.state = useState({ ...this.props });
        }
    }
    const props = { offset: 0, limit: 4, total: 10, onUpdate() {} };

    await mountWithCleanup(Host, { props });
    await contains(".o_pager_value").click();
    expect("input.o_pager_value").toHaveCount(1);
    await contains("input.o_pager_value").click();
    await animationFrame();
    expect("input.o_pager_value").toHaveCount(1, {
        message: "clicking inside the open input keeps edit mode",
    });

    queryOne("input.o_pager_value").dispatchEvent(
        new PointerEvent("pointerdown", { bubbles: true, composed: true }),
    );
    await animationFrame();
    expect("input.o_pager_value").toHaveCount(1, {
        message: "a bare pointerdown inside the input keeps edit mode",
    });

    await contains(".outside").click();
    await animationFrame();
    expect("input.o_pager_value").toHaveCount(0, {
        message: "clicking outside still leaves edit mode",
    });
});

test.tags("desktop");
test("a pager listens to no pointerdown on the window; leaving the input ends the edit", async () => {
    const registered = [];
    const { addEventListener } = window;
    patchWithCleanup(window, {
        /** @type {typeof addEventListener} */
        addEventListener(type, listener, options) {
            registered.push(type);
            return addEventListener.call(this, type, listener, options);
        },
    });
    await mountWithCleanup(PagerController, {
        props: { offset: 0, limit: 4, total: 10, onUpdate() {} },
    });
    await animationFrame();
    expect(registered.filter((type) => type === "pointerdown")).toEqual([]);

    await contains(".o_pager_value").click();
    expect("input.o_pager_value").toHaveCount(1);
    queryOne("input.o_pager_value").blur();
    await animationFrame();
    expect("input.o_pager_value").toHaveCount(0);
});

for (const direction of /** @type {const} */ ([-1, 1])) {
    for (const reject of [false, true]) {
        test(`navigation ${direction} waits for a ${reject ? "rejected" : "successful"} update`, async () => {
            const load = new Deferred();
            const pager = await mountWithCleanup(Pager, {
                props: {
                    offset: 0,
                    limit: 5,
                    total: 10,
                    updateTotal: direction === -1 ? async () => 23 : undefined,
                    onUpdate: (range) => {
                        expect.step(`load ${range.offset}`);
                        return load;
                    },
                },
            });
            // Observe the original promise without allowing a detached rejection
            // to end the test before its navigation contract can be checked.
            patchWithCleanup(pager, {
                update(...args) {
                    const update = super.update(...args);
                    update.catch(() => {});
                    return update;
                },
            });
            let outcome = "pending";
            const navigation = pager.navigate(direction).then(
                () => {
                    outcome = "resolved";
                },
                () => {
                    outcome = "rejected";
                },
            );
            await animationFrame();
            expect.verifySteps([`load ${direction === -1 ? 20 : 5}`]);
            expect(outcome).toBe("pending");
            expect(pager.state.isDisabled).toBe(true);
            if (reject) {
                load.reject(new Error("page load failed"));
            } else {
                load.resolve();
            }
            await navigation;
            await animationFrame();
            expect(outcome).toBe(reject ? "rejected" : "resolved");
            expect(pager.state.isDisabled).toBe(false);
        });
    }
}
