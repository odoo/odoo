import { test, expect } from "@odoo/hoot";
import { Deferred, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { click, press } from "@odoo/hoot-dom";
import { Pager } from "@web/core/pager/pager";
import { Component, useState, xml } from "@odoo/owl";
import { contains, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
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

test.tags("desktop")("basic interactions on desktop", async () => {
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

test.tags("mobile")("basic interactions on mobile", async () => {
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
    await animationFrame(); // transition

    expect(".o_pager_indicator").toHaveCount(1);
    expect(".o_pager_indicator .o_pager_value").toHaveText("5-8");
    await runAllTimers();
    await animationFrame();

    expect(".o_pager_indicator").toHaveCount(0);

    await click(".o_pager button.o_pager_previous");
    await animationFrame();
    await animationFrame(); // transition

    expect(".o_pager_indicator").toHaveCount(1);
    expect(".o_pager_indicator .o_pager_value").toHaveText("1-4");
    await runAllTimers();
    await animationFrame();

    expect(".o_pager_indicator").toHaveCount(0);
});

test.tags("desktop")("edit the pager", async () => {
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

test.tags("desktop")("keydown on pager with same value", async () => {
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

test.tags("desktop")("pager value formatting", async () => {
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
            // The goal here is to test the reactivity of the pager; in a
            // typical views, we disable the pager after switching page
            // to avoid switching twice with the same action (double click).
            async onUpdate(data) {
                // 1. Simulate a (long) server action
                await reloadPromise;
                // 2. Update the view with loaded data
                await pager.updateProps(data);
            },
        },
    });

    // Click and check button is disabled
    await click(".o_pager button.o_pager_next");
    await animationFrame();
    expect(".o_pager button.o_pager_next").toHaveAttribute("disabled");

    await click(".o_pager button.o_pager_previous");
    await animationFrame();
    expect(".o_pager button.o_pager_previous").toHaveAttribute("disabled");
});

test.tags("desktop")("pager disabling on desktop", async () => {
    const reloadPromise = new Deferred();
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            // The goal here is to test the reactivity of the pager; in a
            // typical views, we disable the pager after switching page
            // to avoid switching twice with the same action (double click).
            async onUpdate(data) {
                // 1. Simulate a (long) server action
                await reloadPromise;
                // 2. Update the view with loaded data
                await pager.updateProps(data);
            },
        },
    });

    await click(".o_pager button.o_pager_next");
    await animationFrame();
    // Try to edit the pager value
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

test.tags("desktop")("desktop input interaction", async () => {
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

test.tags("desktop")("updateTotal props: click on total", async () => {
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

test.tags("desktop")("updateTotal props: click next", async () => {
    let tempTotal = 10;
    const realTotal = 18;
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: tempTotal,
            async onUpdate(data) {
                tempTotal = Math.min(realTotal, Math.max(tempTotal, data.offset + data.limit));
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

test.tags("desktop")("updateTotal props: edit input", async () => {
    let tempTotal = 10;
    const realTotal = 18;
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: tempTotal,
            async onUpdate(data) {
                tempTotal = Math.min(realTotal, Math.max(tempTotal, data.offset + data.limit));
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

test.tags("desktop")("updateTotal props: can use next even if single page", async () => {
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

test.tags("desktop")("updateTotal props: click previous", async () => {
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
    await animationFrame(); // double call to updateProps

    expect(".o_pager_value").toHaveText("21-23");
    expect(".o_pager_limit").toHaveText("23");
    expect(".o_pager_limit").not.toHaveClass("o_pager_limit_fetch");
});
