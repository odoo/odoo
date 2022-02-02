/** @odoo-module **/

import { Pager } from "@web/core/pager/pager";
import { makeTestEnv } from "../helpers/mock_env";
import {
    click,
    triggerEvent,
    makeDeferred,
    mount,
    nextTick,
    getFixture,
    triggerEvents,
} from "../helpers/utils";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";

const { Component, useState, xml } = owl;

const serviceRegistry = registry.category("services");

class PagerController extends Component {
    setup() {
        this.state = useState({ ...this.props });
    }
    async updateProps(nextProps) {
        Object.assign(this.state, nextProps);
        await nextTick();
    }
}
PagerController.template = xml`<Pager t-props="state" />`;
PagerController.components = { Pager };

async function makePager(props) {
    serviceRegistry.add("ui", uiService);
    const env = await makeTestEnv();
    const pager = await mount(PagerController, getFixture(), { env, props });
    return pager;
}

QUnit.module("Components", () => {
    QUnit.module("Pager");

    QUnit.test("basic interactions", async function (assert) {
        assert.expect(2);

        const pager = await makePager({
            offset: 0,
            limit: 4,
            total: 10,
            onUpdate(data) {
                pager.updateProps(data);
            },
        });
        assert.strictEqual(
            pager.el.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "1-4",
            "currentMinimum should be set to 1"
        );

        await click(pager.el.querySelector(`.o_pager button.o_pager_next`));
        assert.strictEqual(
            pager.el.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "5-8",
            "currentMinimum should now be 5"
        );
    });

    QUnit.test("edit the pager", async function (assert) {
        assert.expect(4);

        const pager = await makePager({
            offset: 0,
            limit: 4,
            total: 10,
            onUpdate(data) {
                pager.updateProps(data);
            },
        });

        await click(pager.el, ".o_pager_value");

        assert.containsOnce(pager, "input", "the pager should contain an input");
        assert.strictEqual(
            pager.el.querySelector(`.o_pager_counter .o_pager_value`).value,
            "1-4",
            "the input should have correct value"
        );

        // change the limit
        const input = pager.el.querySelector(`.o_pager_counter input.o_pager_value`);
        input.value = "1-6";
        await triggerEvents(input, null, ["change", "blur"]);

        assert.containsNone(pager, "input", "the pager should not contain an input anymore");
        assert.strictEqual(
            pager.el.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "1-6",
            "the limit should have been updated"
        );
    });

    QUnit.test("keydown on pager with same value", async function (assert) {
        assert.expect(7);

        const pager = await makePager({
            offset: 0,
            limit: 4,
            total: 10,
            onUpdate() {
                assert.step("pager-changed");
            },
        });

        // Enter edit mode
        await click(pager.el, ".o_pager_value");

        assert.containsOnce(pager.el, "input");
        assert.strictEqual(pager.el.querySelector(`.o_pager_counter .o_pager_value`).value, "1-4");
        assert.verifySteps([]);

        // Exit edit mode
        await triggerEvent(pager.el, "input", "keydown", { key: "Enter" });

        assert.containsNone(pager.el, "input");
        assert.strictEqual(
            pager.el.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "1-4"
        );
        assert.verifySteps(["pager-changed"]);
    });

    QUnit.test("pager value formatting", async function (assert) {
        assert.expect(8);

        const pager = await makePager({
            offset: 0,
            limit: 4,
            total: 10,
            onUpdate(data) {
                pager.updateProps(data);
            },
        });

        assert.strictEqual(
            pager.el.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "1-4",
            "Initial value should be correct"
        );

        async function inputAndAssert(inputValue, expected, reason) {
            await click(pager.el.querySelector(`.o_pager_counter .o_pager_value`));
            const inputEl = pager.el.querySelector(`.o_pager_counter input.o_pager_value`);
            inputEl.value = inputValue;
            await triggerEvents(inputEl, null, ["change", "blur"]);
            assert.strictEqual(
                pager.el.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
                expected,
                `Pager value should be "${expected}" when given "${inputValue}": ${reason}`
            );
        }

        await inputAndAssert("4-4", "4", "values are squashed when minimum = maximum");
        await inputAndAssert("1-11", "1-10", "maximum is floored to total when out of range");
        await inputAndAssert("20-15", "10", "combination of the 2 assertions above");
        await inputAndAssert("6-5", "10", "fallback to previous value when minimum > maximum");
        await inputAndAssert(
            "definitelyValidNumber",
            "10",
            "fallback to previous value if not a number"
        );
        await inputAndAssert(
            " 1 ,  2   ",
            "1-2",
            "value is normalized and accepts several separators"
        );
        await inputAndAssert("3  8", "3-8", "value accepts whitespace(s) as a separator");
    });

    QUnit.test("pager disabling", async function (assert) {
        assert.expect(9);

        const reloadPromise = makeDeferred();

        const pager = await makePager({
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
        });
        const pagerButtons = pager.el.querySelectorAll("button");

        // Click twice
        await click(pager.el.querySelector(`.o_pager button.o_pager_next`));
        await click(pager.el.querySelector(`.o_pager button.o_pager_next`));
        // Try to edit the pager value
        await click(pager.el, ".o_pager_value");

        assert.strictEqual(pagerButtons.length, 2, "the two buttons should be displayed");
        assert.ok(pagerButtons[0].disabled, "'previous' is disabled");
        assert.ok(pagerButtons[1].disabled, "'next' is disabled");
        assert.strictEqual(
            pager.el.querySelector(".o_pager_value").tagName,
            "SPAN",
            "pager edition is prevented"
        );

        // Server action is done
        reloadPromise.resolve();
        await nextTick();

        assert.strictEqual(pagerButtons.length, 2, "the two buttons should be displayed");
        assert.notOk(pagerButtons[0].disabled, "'previous' is enabled");
        assert.notOk(pagerButtons[1].disabled, "'next' is enabled");
        assert.strictEqual(
            pager.el.querySelector(`.o_pager_counter .o_pager_value`).textContent.trim(),
            "5-8",
            "value has been updated"
        );

        await click(pager.el, ".o_pager_value");

        assert.strictEqual(
            pager.el.querySelector(".o_pager_value").tagName,
            "INPUT",
            "pager edition is re-enabled"
        );
    });

    QUnit.test("input interaction", async function (assert) {
        const pager = await makePager({
            offset: 0,
            limit: 4,
            total: 10,
            onUpdate(data) {
                pager.updateProps(data);
            },
        });

        await click(pager.el, ".o_pager_value");
        assert.containsOnce(pager, "input", "the pager should contain an input");
        assert.strictEqual(
            pager.el.querySelector("input"),
            document.activeElement,
            "pager input is focused"
        );

        await triggerEvent(pager.el, null, "mousedown");
        assert.containsNone(pager, "input", "the pager should not contain an input");
    });
});
