odoo.define('web.action_menus_tests', function (require) {
    "use strict";

    const ActionMenus = require('web.ActionMenus');
    const Registry = require('web.Registry');
    const testUtils = require('web.test_utils');

    const { Component } = owl;
    const { createComponent } = testUtils;

    QUnit.module('Components', {
        beforeEach() {
            this.action = {
                res_model: 'hobbit',
            };
            this.view = {
                // needed by google_drive module, makes sense to give a view anyway.
                type: 'form',
            };
            this.props = {
                activeIds: [23],
                context: {},
                items: {
                    action: [
                        { action: { id: 1 }, name: "What's taters, precious ?", id: 1 },
                    ],
                    print: [
                        { action: { id: 2 }, name: "Po-ta-toes", id: 2 },
                    ],
                    other: [
                        { description: "Boil'em", callback() { } },
                        { description: "Mash'em", callback() { } },
                        { description: "Stick'em in a stew", url: '#stew' },
                    ],
                },
            };
            // Patch the registry of the action menus
            this.actionMenusRegistry = ActionMenus.registry;
            ActionMenus.registry = new Registry();
        },
        afterEach() {
            ActionMenus.registry = this.actionMenusRegistry;
        },
    }, function () {

        QUnit.module('ActionMenus');

        QUnit.test('basic interactions', async function (assert) {
            assert.expect(10);

            const actionMenus = await createComponent(ActionMenus, {
                env: {
                    action: this.action,
                    view: this.view,
                },
                props: this.props,
            });

            const dropdowns = actionMenus.el.getElementsByClassName('dropdown');
            assert.strictEqual(dropdowns.length, 2, "ActionMenus should contain 2 menus");
            assert.strictEqual(dropdowns[0].querySelector('.o_dropdown_title').innerText.trim(), "Print");
            assert.strictEqual(dropdowns[1].querySelector('.o_dropdown_title').innerText.trim(), "Action");
            assert.containsNone(actionMenus, '.o-dropdown-menu');

            await testUtils.controlPanel.toggleActionMenu(actionMenus, "Action");

            assert.containsOnce(actionMenus, '.o-dropdown-menu');
            assert.containsN(actionMenus, '.o-dropdown-menu .o_menu_item', 4);
            const actionsTexts = [...dropdowns[1].querySelectorAll('.o_menu_item')].map(el => el.innerText.trim());
            assert.deepEqual(actionsTexts, [
                "Boil'em",
                "Mash'em",
                "Stick'em in a stew",
                "What's taters, precious ?",
            ], "callbacks should appear before actions");

            await testUtils.controlPanel.toggleActionMenu(actionMenus, "Print");

            assert.containsOnce(actionMenus, '.o-dropdown-menu');
            assert.containsN(actionMenus, '.o-dropdown-menu .o_menu_item', 1);

            await testUtils.controlPanel.toggleActionMenu(actionMenus, "Print");

            assert.containsNone(actionMenus, '.o-dropdown-menu');
        });

        QUnit.test("empty action menus", async function (assert) {
            assert.expect(1);

            ActionMenus.registry.add("test", { Component, getProps: () => false });
            this.props.items = {};

            const actionMenus = await createComponent(ActionMenus, {
                env: {
                    action: this.action,
                    view: this.view,
                },
                props: this.props,
            });

            assert.containsNone(actionMenus, ".o_cp_action_menus > *");
        });

        QUnit.test('execute action', async function (assert) {
            assert.expect(4);

            const actionMenus = await createComponent(ActionMenus, {
                env: {
                    action: this.action,
                    view: this.view,
                },
                props: this.props,
                intercepts: {
                    'do-action': ev => assert.step('do-action'),
                },
                async mockRPC(route, args) {
                    switch (route) {
                        case '/web/action/load':
                            const expectedContext = {
                                active_id: 23,
                                active_ids: [23],
                                active_model: 'hobbit',
                            };
                            assert.deepEqual(args.context, expectedContext);
                            assert.step('load-action');
                            return { context: {}, flags: {} };
                        default:
                            return this._super(...arguments);

                    }
                },
            });

            await testUtils.controlPanel.toggleActionMenu(actionMenus, "Action");
            await testUtils.controlPanel.toggleMenuItem(actionMenus, "What's taters, precious ?");

            assert.verifySteps(['load-action', 'do-action']);
        });

        QUnit.test('execute callback action', async function (assert) {
            assert.expect(2);

            const callbackPromise = testUtils.makeTestPromise();
            this.props.items.other[0].callback = function (items) {
                assert.strictEqual(items.length, 1);
                assert.strictEqual(items[0].description, "Boil'em");
                callbackPromise.resolve();
            };

            const actionMenus = await createComponent(ActionMenus, {
                env: {
                    action: this.action,
                    view: this.view,
                },
                props: this.props,
                async mockRPC(route, args) {
                    switch (route) {
                        case '/web/action/load':
                            throw new Error("No action should be loaded.");
                        default:
                            return this._super(...arguments);
                    }
                },
            });

            await testUtils.controlPanel.toggleActionMenu(actionMenus, "Action");
            await testUtils.controlPanel.toggleMenuItem(actionMenus, "Boil'em");

            await callbackPromise;
        });

        QUnit.test('execute print action', async function (assert) {
            assert.expect(4);

            const actionMenus = await createComponent(ActionMenus, {
                env: {
                    action: this.action,
                    view: this.view,
                },
                intercepts: {
                    'do-action': ev => assert.step('do-action'),
                },
                props: this.props,
                async mockRPC(route, args) {
                    switch (route) {
                        case '/web/action/load':
                            const expectedContext = {
                                active_id: 23,
                                active_ids: [23],
                                active_model: 'hobbit',
                            };
                            assert.deepEqual(args.context, expectedContext);
                            assert.step('load-action');
                            return { context: {}, flags: {} };
                        default:
                            return this._super(...arguments);

                    }
                },
            });

            await testUtils.controlPanel.toggleActionMenu(actionMenus, "Print");
            await testUtils.controlPanel.toggleMenuItem(actionMenus, "Po-ta-toes");

            assert.verifySteps(['load-action', 'do-action']);
        });

        QUnit.test('execute url action', async function (assert) {
            assert.expect(2);

            const actionMenus = await createComponent(ActionMenus, {
                env: {
                    action: this.action,
                    services: {
                        navigate(url) {
                            assert.step(url);
                        },
                    },
                    view: this.view,
                },
                props: this.props,
                async mockRPC(route, args) {
                    switch (route) {
                        case '/web/action/load':
                            throw new Error("No action should be loaded.");
                        default:
                            return this._super(...arguments);
                    }
                },
            });

            await testUtils.controlPanel.toggleActionMenu(actionMenus, "Action");
            await testUtils.controlPanel.toggleMenuItem(actionMenus, "Stick'em in a stew");

            assert.verifySteps(['#stew']);
        });

        QUnit.test('execute action with context', async function (assert) {
            assert.expect(1);
            const actionMenus = await createComponent(ActionMenus, {
                env: {
                    action: this.action,
                    view: this.view,
                },
                props: {
                    ...this.props,
                    isDomainSelected:  true,
                    context: {
                        allowed_company_ids: [112],
                    },
                },
                async mockRPC(route, args) {
                    if (route === "/web/dataset/call_kw/hobbit/search"){
                        assert.deepEqual(args.kwargs.context, { allowed_company_ids: [112] }, "The kwargs should contains the right context");
                    }
                    return this._super(...arguments);
                },
            });

            await testUtils.controlPanel.toggleActionMenu(actionMenus, "Action");
            await testUtils.controlPanel.toggleMenuItem(actionMenus, "What's taters, precious ?");
        });
    });
});
