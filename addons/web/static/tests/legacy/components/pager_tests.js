odoo.define('web.pager_tests', function (require) {
    "use strict";

    const Pager = require('web.Pager');
    const testUtils = require('web.test_utils');
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    const { createComponent } = testUtils;

    const { xml, useState } = owl;

    class PagerController extends LegacyComponent {
        setup() {
            this.state = useState({ ...this.props });
        }
        async updateProps(nextProps) {
            Object.assign(this.state, nextProps);
            await testUtils.nextTick();
        }
    }
    PagerController.template = xml`<Pager t-props="state" />`;
    PagerController.components = { Pager };

    QUnit.module('Components', {}, function () {

        QUnit.module('Legacy Pager');

        QUnit.test('basic interactions', async function (assert) {
            assert.expect(2);

            const pager = await createComponent(PagerController, {
                props: {
                    currentMinimum: 1,
                    limit: 4,
                    size: 10,
                    onPagerChanged: function (detail) {
                        pager.updateProps(detail);
                    },
                },
            });

            assert.strictEqual(testUtils.controlPanel.getPagerValue(pager), "1-4",
                "currentMinimum should be set to 1");

            await testUtils.controlPanel.pagerNext(pager);

            assert.strictEqual(testUtils.controlPanel.getPagerValue(pager), "5-8",
                "currentMinimum should now be 5");
        });

        QUnit.test('edit the pager', async function (assert) {
            assert.expect(4);

            const pager = await createComponent(PagerController, {
                props: {
                    currentMinimum: 1,
                    limit: 4,
                    size: 10,
                    onPagerChanged: function (detail) {
                        pager.updateProps(detail);
                    },
                },
            });

            await testUtils.dom.click(pager.el.querySelector('.o_pager_value'));

            assert.containsOnce(pager, 'input',
                "the pager should contain an input");
            assert.strictEqual(testUtils.controlPanel.getPagerValue(pager), "1-4",
                "the input should have correct value");

            // change the limit
            await testUtils.controlPanel.setPagerValue(pager, "1-6");

            assert.containsNone(pager, 'input',
                "the pager should not contain an input anymore");
            assert.strictEqual(testUtils.controlPanel.getPagerValue(pager), "1-6",
                "the limit should have been updated");
        });

        QUnit.test("keydown on pager with same value", async function (assert) {
            assert.expect(7);

            const pager = await createComponent(PagerController, {
                props: {
                    currentMinimum: 1,
                    limit: 4,
                    size: 10,
                    onPagerChanged: () => assert.step("pager-changed"),
                },
            });

            // Enter edit mode
            await testUtils.dom.click(pager.el.querySelector('.o_pager_value'));

            assert.containsOnce(pager, "input");
            assert.strictEqual(testUtils.controlPanel.getPagerValue(pager), "1-4");
            assert.verifySteps([]);

            // Exit edit mode
            await testUtils.dom.triggerEvent(pager.el.querySelector('input'), "keydown", { key: "Enter" });

            assert.containsNone(pager, "input");
            assert.strictEqual(testUtils.controlPanel.getPagerValue(pager), "1-4");
            assert.verifySteps(["pager-changed"]);
        });

        QUnit.test('pager value formatting', async function (assert) {
            assert.expect(8);

            const pager = await createComponent(PagerController, {
                props: {
                    currentMinimum: 1,
                    limit: 4,
                    size: 10,
                    onPagerChanged: (detail) => {
                        pager.updateProps(detail);
                    },
                },
            });

            assert.strictEqual(testUtils.controlPanel.getPagerValue(pager), "1-4", "Initial value should be correct");

            async function inputAndAssert(input, expected, reason) {
                await testUtils.controlPanel.setPagerValue(pager, input);
                assert.strictEqual(testUtils.controlPanel.getPagerValue(pager), expected,
                    `Pager value should be "${expected}" when given "${input}": ${reason}`);
            }

            await inputAndAssert("4-4", "4", "values are squashed when minimum = maximum");
            await inputAndAssert("1-11", "1-10", "maximum is floored to size when out of range");
            await inputAndAssert("20-15", "10", "combination of the 2 assertions above");
            await inputAndAssert("6-5", "10", "fallback to previous value when minimum > maximum");
            await inputAndAssert("definitelyValidNumber", "10", "fallback to previous value if not a number");
            await inputAndAssert(" 1 ,  2   ", "1-2", "value is normalized and accepts several separators");
            await inputAndAssert("3  8", "3-8", "value accepts whitespace(s) as a separator");
        });

        QUnit.test('pager disabling', async function (assert) {
            assert.expect(10);

            const reloadPromise = testUtils.makeTestPromise();
            const pager = await createComponent(PagerController, {
                props: {
                    currentMinimum: 1,
                    limit: 4,
                    size: 10,
                    // The goal here is to test the reactivity of the pager; in a
                    // typical views, we disable the pager after switching page
                    // to avoid switching twice with the same action (double click).
                    onPagerChanged: async function (detail) {
                        // 1. Simulate a (long) server action
                        await reloadPromise;
                        // 2. Update the view with loaded data
                        pager.updateProps(detail);
                    },
                },
            });
            const pagerButtons = pager.el.querySelectorAll('button');

            // Click and check button is disabled
            await testUtils.controlPanel.pagerNext(pager);
            assert.ok(pager.el.querySelector('button.o_pager_next').disabled);
            // Try to edit the pager value
            await testUtils.dom.click(pager.el.querySelector('.o_pager_value'));

            assert.strictEqual(pagerButtons.length, 2, "the two buttons should be displayed");
            assert.ok(pagerButtons[0].disabled, "'previous' is disabled");
            assert.ok(pagerButtons[1].disabled, "'next' is disabled");
            assert.strictEqual(pager.el.querySelector('.o_pager_value').tagName, 'SPAN',
                "pager edition is prevented");

            // Server action is done
            reloadPromise.resolve();
            await testUtils.nextTick();

            assert.strictEqual(pagerButtons.length, 2, "the two buttons should be displayed");
            assert.notOk(pagerButtons[0].disabled, "'previous' is enabled");
            assert.notOk(pagerButtons[1].disabled, "'next' is enabled");
            assert.strictEqual(testUtils.controlPanel.getPagerValue(pager), "5-8", "value has been updated");

            await testUtils.dom.click(pager.el.querySelector('.o_pager_value'));

            assert.strictEqual(pager.el.querySelector('.o_pager_value').tagName, 'INPUT',
                "pager edition is re-enabled");
        });
    });
});
