import { test, expect } from "@odoo/hoot";
import { Deferred, animationFrame } from "@odoo/hoot-mock";
import { click, press } from "@odoo/hoot-dom";
import { Pager } from "@web/core/pager/pager";
import { Component, useState, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

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
            onUpdate(data) {
                pager.updateProps(data);
            },
        },
    });

    expect(".o_pager_counter .o_pager_value").toHaveText("1-4");

    click(".o_pager button.o_pager_next");
    await animationFrame();

    expect(".o_pager_counter .o_pager_value").toHaveText("5-8");
});

test("edit the pager", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            onUpdate(data) {
                pager.updateProps(data);
            },
        },
    });

    click(".o_pager_value");
    await animationFrame();

    expect("input").toHaveCount(1);
    expect(".o_pager_counter .o_pager_value").toHaveValue("1-4");

    await contains("input.o_pager_value").edit("1-6");
    click(document.body);
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

    click(".o_pager_value");
    await animationFrame();

    expect("input").toHaveCount(1);
    expect(".o_pager_counter .o_pager_value").toHaveValue("1-4");
    expect([]).toVerifySteps();

    press("Enter");
    await animationFrame();
    expect("input").toHaveCount(0);
    expect(".o_pager_counter .o_pager_value").toHaveText("1-4");
    expect(["pager-changed"]).toVerifySteps();
});

test("pager value formatting", async () => {
    expect.assertions(8);
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            onUpdate(data) {
                pager.updateProps(data);
            },
        },
    });

    expect(".o_pager_counter .o_pager_value").toHaveText("1-4");

    async function inputAndAssert(inputValue, expected) {
        click(".o_pager_counter .o_pager_value");
        await animationFrame();
        await contains("input.o_pager_value").edit(inputValue);
        click(document.body);
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
                pager.updateProps(data);
            },
        },
    });

    // Click and check button is disabled
    click(".o_pager button.o_pager_next");
    await animationFrame();
    expect(".o_pager button.o_pager_next").toHaveAttribute("disabled");
    // Try to edit the pager value
    click(".o_pager_value");
    await animationFrame();

    expect("button").toHaveCount(2);
    expect("button:nth-child(1)").toHaveAttribute("disabled");
    expect("button:nth-child(2)").toHaveAttribute("disabled");
    expect("span.o_pager_value").toHaveCount(1);

    reloadPromise.resolve();
    await animationFrame();

    expect("button").toHaveCount(2);
    expect("button:nth-child(1)").not.toHaveAttribute("disabled");
    expect("button:nth-child(2)").not.toHaveAttribute("disabled");
    expect(".o_pager_counter .o_pager_value").toHaveText("5-8");

    click(".o_pager_value");
    await animationFrame();

    expect("input.o_pager_value").toHaveCount(1);
});

test.tags("desktop")("desktop input interaction", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            onUpdate(data) {
                pager.updateProps(data);
            },
        },
    });
    click(".o_pager_value");
    await animationFrame();

    expect("input").toHaveCount(1);
    expect("input").toBeFocused();
    click(document.body);
    await animationFrame();
    expect("input").toHaveCount(0);
});

test.tags("mobile")("mobile input interaction", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 4,
            total: 10,
            onUpdate(data) {
                pager.updateProps(data);
            },
        },
    });
    click(".o_pager_value");
    await animationFrame();
    expect(document.body).toBeFocused();
    expect("input").toHaveCount(1);

    click(".o_pager_value");
    await animationFrame();
    expect("input").toHaveCount(1);
    expect("input").toBeFocused();
    click(document.body);
    await animationFrame();
    expect("input").toHaveCount(0);
});

test("updateTotal props: click on total", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: 10,
            onUpdate() {},
            updateTotal() {
                pager.updateProps({ total: 25, updateTotal: undefined });
            },
        },
    });

    expect(".o_pager_value").toHaveText("1-5");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    click(".o_pager_limit_fetch");
    await animationFrame();
    expect(".o_pager_value").toHaveText("1-5");
    expect(".o_pager_limit").toHaveText("25");
    expect(".o_pager_limit").not.toHaveClass("o_pager_limit_fetch");
});

test("updateTotal props: click next", async () => {
    let tempTotal = 10;
    const realTotal = 18;
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: tempTotal,
            onUpdate(data) {
                tempTotal = Math.min(realTotal, Math.max(tempTotal, data.offset + data.limit));
                const nextProps = { ...data, total: tempTotal };
                if (tempTotal === realTotal) {
                    nextProps.updateTotal = undefined;
                }
                pager.updateProps(nextProps);
            },
            updateTotal() {},
        },
    });

    expect(".o_pager_value").toHaveText("1-5");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    click(".o_pager_next");
    await animationFrame();
    expect(".o_pager_value").toHaveText("6-10");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    click(".o_pager_next");
    await animationFrame();
    expect(".o_pager_value").toHaveText("11-15");
    expect(".o_pager_limit").toHaveText("15+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    click(".o_pager_next");
    await animationFrame();
    expect(".o_pager_value").toHaveText("16-18");
    expect(".o_pager_limit").toHaveText("18");
    expect(".o_pager_limit").not.toHaveClass("o_pager_limit_fetch");
});

test("updateTotal props: edit input", async () => {
    let tempTotal = 10;
    const realTotal = 18;
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: tempTotal,
            onUpdate(data) {
                tempTotal = Math.min(realTotal, Math.max(tempTotal, data.offset + data.limit));
                const nextProps = { ...data, total: tempTotal };
                if (tempTotal === realTotal) {
                    nextProps.updateTotal = undefined;
                }
                pager.updateProps(nextProps);
            },
            updateTotal() {},
        },
    });

    expect(".o_pager_value").toHaveText("1-5");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    click(".o_pager_value");
    await animationFrame();
    await contains("input.o_pager_value").edit("3-8");
    click(document.body);
    await animationFrame();

    expect(".o_pager_value").toHaveText("3-8");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    click(".o_pager_value");
    await animationFrame();
    await contains("input.o_pager_value").edit("3-20");
    click(document.body);
    await animationFrame();
    expect(".o_pager_value").toHaveText("3-18");
    expect(".o_pager_limit").toHaveText("18");
    expect(".o_pager_limit").not.toHaveClass("o_pager_limit_fetch");
});

test("updateTotal props: can use next even if single page", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: 5,
            onUpdate(data) {
                pager.updateProps({ ...data, total: 10 });
            },
            updateTotal() {},
        },
    });

    expect(".o_pager_value").toHaveText("1-5");
    expect(".o_pager_limit").toHaveText("5+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    click(".o_pager_next");
    await animationFrame();

    expect(".o_pager_value").toHaveText("6-10");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");
});

test("updateTotal props: click previous", async () => {
    const pager = await mountWithCleanup(PagerController, {
        props: {
            offset: 0,
            limit: 5,
            total: 10,
            onUpdate(data) {
                pager.updateProps(data);
            },
            async updateTotal() {
                const total = 23;
                pager.updateProps({ total, updateTotal: undefined });
                return total;
            },
        },
    });

    expect(".o_pager_value").toHaveText("1-5");
    expect(".o_pager_limit").toHaveText("10+");
    expect(".o_pager_limit").toHaveClass("o_pager_limit_fetch");

    click(".o_pager_previous");
    await animationFrame();

    expect(".o_pager_value").toHaveText("21-23");
    expect(".o_pager_limit").toHaveText("23");
    expect(".o_pager_limit").not.toHaveClass("o_pager_limit_fetch");
});
