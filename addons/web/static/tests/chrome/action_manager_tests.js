odoo.define('web.action_manager_tests', function (require) {
"use strict";

const ActionManager = require('web.ActionManager');
const AbstractAction = require('web.AbstractAction');
const AbstractStorageService = require('web.AbstractStorageService');
const BasicFields = require('web.basic_fields');
const { CrashManager } = require('web.CrashManager');
const core = require('web.core');
const ListController = require('web.ListController');
const Notification = require('web.Notification');
const NotificationService = require('web.NotificationService');
const RamStorage = require('web.RamStorage');
const ReportClientAction = require('report.client_action');
const ReportService = require('web.ReportService');
const SessionStorageService = require('web.SessionStorageService');
const StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
const testUtils = require('web.test_utils');
const utils = require('web.utils');
const Widget = require('web.Widget');

const { createWebClient, nextTick } = testUtils;

const cpHelpers = testUtils.controlPanel;
const { doAction, loadState }  = testUtils.actionManager;

QUnit.module('ActionManager', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "many2one", relation: 'partner'},
                    o2m: {string: "One2Many", type: "one2many", relation: 'partner', relation_field: 'bar'},
                },
                records: [
                    {id: 1, display_name: "First record", foo: "yop", bar: 2, o2m: [2, 3]},
                    {id: 2, display_name: "Second record", foo: "blip", bar: 1, o2m: [1, 4, 5]},
                    {id: 3, display_name: "Third record", foo: "gnap", bar: 1, o2m: []},
                    {id: 4, display_name: "Fourth record", foo: "plop", bar: 2, o2m: []},
                    {id: 5, display_name: "Fifth record", foo: "zoup", bar: 2, o2m: []},
                ],
            },
            pony: {
                fields: {
                    name: {string: 'Name', type: 'char'},
                },
                records: [
                    {id: 4, name: 'Twilight Sparkle'},
                    {id: 6, name: 'Applejack'},
                    {id: 9, name: 'Fluttershy'}
                ],
            },
        };

        this.actions = [{
            id: 1,
            name: 'Partners Action 1',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[1, 'kanban']],
        }, {
            id: 2,
            type: 'ir.actions.server',
        }, {
            id: 3,
            name: 'Partners',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'list'], [1, 'kanban'], [false, 'form']],
        }, {
            id: 4,
            name: 'Partners Action 4',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[1, 'kanban'], [2, 'list'], [false, 'form']],
        }, {
            id: 5,
            name: 'Create a Partner',
            res_model: 'partner',
            target: 'new',
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
        }, {
            id: 6,
            name: 'Partner',
            res_id: 2,
            res_model: 'partner',
            target: 'inline',
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
        }, {
            id: 7,
            name: "Some Report",
            report_name: 'some_report',
            report_type: 'qweb-pdf',
            type: 'ir.actions.report',
        }, {
            id: 8,
            name: 'Favorite Ponies',
            res_model: 'pony',
            type: 'ir.actions.act_window',
            views: [[false, 'list'], [false, 'form']],
        }, {
            id: 9,
            name: 'A Client Action',
            tag: 'ClientAction',
            type: 'ir.actions.client',
        }, {
            id: 10,
            type: 'ir.actions.act_window_close',
        }, {
            id: 11,
            name: "Another Report",
            report_name: 'another_report',
            report_type: 'qweb-pdf',
            type: 'ir.actions.report',
            close_on_report_download: true,
        }, {
            id: 24,
            name: 'Partner',
            res_id: 2,
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[666, 'form']],
        }, {
            id: 25,
            name: 'Create a Partner',
            res_model: 'partner',
            target: 'new',
            type: 'ir.actions.act_window',
            views: [[1, 'form']],
        }];

        this.archs = {
            // kanban views
            'partner,1,kanban': '<kanban><templates><t t-name="kanban-box">' +
                    '<div class="oe_kanban_global_click"><field name="foo"/></div>' +
                '</t></templates></kanban>',

            // list views
            'partner,false,list': '<tree><field name="foo"/></tree>',
            'partner,2,list': '<tree limit="3"><field name="foo"/></tree>',
            'pony,false,list': '<tree><field name="name"/></tree>',

            // form views
            'partner,false,form': '<form>' +
                    '<header>' +
                        '<button name="object" string="Call method" type="object"/>' +
                        '<button name="4" string="Execute action" type="action"/>' +
                    '</header>' +
                    '<group>' +
                        '<field name="display_name"/>' +
                        '<field name="foo"/>' +
                    '</group>' +
                '</form>',

            'partner,1,form': `
                <form>
                    <footer>
                        <button class="btn-primary" string="Save" special="save"/>
                    </footer>
                </form>`,

             'partner,666,form': `<form>
                    <header></header>
                    <sheet>
                        <div class="oe_button_box" name="button_box" modifiers="{}">
                            <button class="oe_stat_button" type="action" name="1" icon="fa-star" context="{'default_partner': active_id}">
                                <field string="Partners" name="o2m" widget="statinfo"/>
                            </button>
                        </div>
                        <field name="display_name"/>
                    </sheet>
                </form>`,

            'pony,false,form': '<form>' +
                    '<field name="name"/>' +
                '</form>',

            // search views
            'partner,false,search': '<search><field name="foo" string="Foo"/></search>',
            'partner,1,search': '<search>' +
                   '<filter name="bar" help="Bar" domain="[(\'bar\', \'=\', 1)]"/>' +
                '</search>',
            'pony,false,search': '<search></search>',
        };
    },
}, function () {
    QUnit.module('Misc');

    QUnit.test('breadcrumbs and actions with target inline', async function (assert) {
        assert.expect(3);

        this.actions[3].views = [[false, 'form']];
        this.actions[3].target = 'inline';

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        await doAction(4);
        assert.ok(!$(webClient.el).find('.o_control_panel').is(':visible'),
            "control panel should not be visible");

        await doAction(1, {clear_breadcrumbs: true});
        assert.ok($(webClient.el).find('.o_control_panel').is(':visible'),
            "control panel should now be visible");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb').text(), "Partners Action 1",
            "should have only one current action visible in breadcrumbs");

        webClient.destroy();
    });

    QUnit.test('no widget memory leaks when doing some action stuff', async function (assert) {
        assert.expect(2);

        const components = new Set();
        const originalMethods = {
            __patch: owl.Component.prototype.__patch,
            __destroy: owl.Component.prototype.__destroy,
        };
        owl.Component.prototype.__patch = function() {
            components.add(this);
            return originalMethods.__patch.call(this, ...arguments);
        };
        owl.Component.prototype.__destroy = function() {
            components.delete(this);
            return originalMethods.__destroy.call(this, ...arguments);
        };

        var delta = 0;
        testUtils.mock.patch(Widget, {
            init: function () {
                delta++;
                this._super.apply(this, arguments);
            },
            destroy: function () {
                delta--;
                this._super.apply(this, arguments);
            },
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        await doAction(8);

        var n = delta;
        await doAction(4);
        // kanban view is loaded, switch to list view
        await testUtils.controlPanel.switchView(webClient, 'list');
        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        // go back to action 8 in breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.strictEqual(delta, n,
            "should have properly destroyed all other widgets");
        webClient.destroy();
        testUtils.mock.unpatch(Widget);
        for (const key in originalMethods) {
            owl.Component.prototype[key] = originalMethods[key];
        }

        assert.strictEqual(components.size, 0);
    });

    QUnit.test('no widget memory leaks when executing actions in dialog', async function (assert) {
        assert.expect(2);

        const components = new Set();
        const originalMethods = {
            __patch: owl.Component.prototype.__patch,
            __destroy: owl.Component.prototype.__destroy,
        };
        owl.Component.prototype.__patch = function() {
            components.add(this);
            return originalMethods.__patch.call(this, ...arguments);
        };
        owl.Component.prototype.__destroy = function() {
            components.delete(this);
            return originalMethods.__destroy.call(this, ...arguments);
        };

        var delta = 0;
        testUtils.mock.patch(Widget, {
            init: function () {
                delta++;
                this._super.apply(this, arguments);
            },
            destroy: function () {
                if (!this.isDestroyed()) {
                    delta--;
                }
                this._super.apply(this, arguments);
            },
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        var n = delta;

        await doAction(5);
        await doAction({type: 'ir.actions.act_window_close'});

        assert.strictEqual(delta, n,
            "should have properly destroyed all widgets");

        webClient.destroy();
        testUtils.mock.unpatch(Widget);
        for (const key in originalMethods) {
            owl.Component.prototype[key] = originalMethods[key];
        }

        assert.strictEqual(components.size, 0);
    });

    QUnit.test('no memory leaks when executing an action while switching view', async function (assert) {
        assert.expect(2);

        const components = new Set();
        const originalMethods = {
            __patch: owl.Component.prototype.__patch,
            __destroy: owl.Component.prototype.__destroy,
        };
        owl.Component.prototype.__patch = function() {
            components.add(this);
            return originalMethods.__patch.call(this, ...arguments);
        };
        owl.Component.prototype.__destroy = function() {
            components.delete(this);
            return originalMethods.__destroy.call(this, ...arguments);
        };

        let def;
        let delta = 0;
        testUtils.mock.patch(Widget, {
            init: function () {
                delta += 1;
                this._super.apply(this, arguments);
            },
            destroy: function () {
                delta -= 1;
                this._super.apply(this, arguments);
            },
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                const result = this._super.apply(this, arguments);
                if (args.method === 'read') {
                    return Promise.resolve(def).then(() => result);
                }
                return result;
            },
        });

        await doAction(4);
        const n = delta;

        await doAction(3, {clear_breadcrumbs: true});

        // switch to the form view (this request is blocked)
        def = testUtils.makeTestPromise();
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        // execute another action meanwhile (don't block this request)
        await doAction(4, {clear_breadcrumbs: true});

        // unblock the switch to the form view in action 3
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.strictEqual(delta, n, "all widgets of action 3 should have been destroyed");

        webClient.destroy();
        testUtils.mock.unpatch(Widget);
        for (const key in originalMethods) {
            owl.Component.prototype[key] = originalMethods[key];
        }

        assert.strictEqual(components.size, 0);
    });

    QUnit.test('no memory leaks when executing an action while loading views', async function (assert) {
        assert.expect(2);

        const components = new Set();
        const originalMethods = {
            __patch: owl.Component.prototype.__patch,
            __destroy: owl.Component.prototype.__destroy,
        };
        owl.Component.prototype.__patch = function() {
            components.add(this);
            return originalMethods.__patch.call(this, ...arguments);
        };
        owl.Component.prototype.__destroy = function() {
            components.delete(this);
            return originalMethods.__destroy.call(this, ...arguments);
        };

        var def;
        var delta = 0;
        testUtils.mock.patch(Widget, {
            init: function () {
                delta += 1;
                this._super.apply(this, arguments);
            },
            destroy: function () {
                delta -= 1;
                this._super.apply(this, arguments);
            },
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
               var result = this._super.apply(this, arguments);
                if (args.method === 'load_views') {
                    return Promise.resolve(def).then(_.constant(result));
                }
                return result;
            },
        });

        // execute action 4 to know the number of widgets it instantiates
        await doAction(4);
        var n = delta;

        // execute a first action (its 'load_views' RPC is blocked)
        def = testUtils.makeTestPromise();
        doAction(3, {clear_breadcrumbs: true});

        // execute another action meanwhile (and unlock the RPC)
        doAction(4, {clear_breadcrumbs: true});
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.strictEqual(n, delta,
            "all widgets of action 3 should have been destroyed");

        webClient.destroy();
        testUtils.mock.unpatch(Widget);
        for (const key in originalMethods) {
            owl.Component.prototype[key] = originalMethods[key];
        }

        assert.strictEqual(components.size, 0);
    });

    QUnit.test('no memory leaks when executing an action while loading data of default view', async function (assert) {
        assert.expect(2);

        const components = new Set();
        const originalMethods = {
            __patch: owl.Component.prototype.__patch,
            __destroy: owl.Component.prototype.__destroy,
        };
        owl.Component.prototype.__patch = function() {
            components.add(this);
            return originalMethods.__patch.call(this, ...arguments);
        };
        owl.Component.prototype.__destroy = function() {
            components.delete(this);
            return originalMethods.__destroy.call(this, ...arguments);
        };

        var def;
        var delta = 0;
        testUtils.mock.patch(Widget, {
            init: function () {
                delta += 1;
                this._super.apply(this, arguments);
            },
            destroy: function () {
                delta -= 1;
                this._super.apply(this, arguments);
            },
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route) {
                var result = this._super.apply(this, arguments);
                if (route === '/web/dataset/search_read') {
                    return Promise.resolve(def).then(_.constant(result));
                }
                return result;
            },
        });

        // execute action 4 to know the number of widgets it instantiates
        await doAction(4);
        var n = delta;

        // execute a first action (its 'search_read' RPC is blocked)
        def = testUtils.makeTestPromise();
        doAction(3, {clear_breadcrumbs: true});

        // execute another action meanwhile (and unlock the RPC)
        doAction(4, {clear_breadcrumbs: true});
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.strictEqual(n, delta,
            "all widgets of action 3 should have been destroyed");

        webClient.destroy();
        testUtils.mock.unpatch(Widget);
        for (const key in originalMethods) {
            owl.Component.prototype[key] = originalMethods[key];
        }

        assert.strictEqual(components.size, 0);
    });

    QUnit.test('action with "no_breadcrumbs" set to true', async function (assert) {
        assert.expect(2);

        _.findWhere(this.actions, {id: 4}).context = {no_breadcrumbs: true};

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(3);
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should be one controller in the breadcrumbs");

        // push another action flagged with 'no_breadcrumbs=true'
        await doAction(4);
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 0,
            "the breadcrumbs should be empty");

        webClient.destroy();
    });

    QUnit.test('on_reverse_breadcrumb handler is correctly called', async function (assert) {
        assert.expect(3);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        // execute action 3 and open a record in form view
        await doAction(3);
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        // execute action 4 without 'on_reverse_breadcrumb' handler, then go back
        await doAction(4);
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.verifySteps([]);

        // execute action 4 with an 'on_reverse_breadcrumb' handler, then go back
        await doAction(4, {
            on_reverse_breadcrumb: function () {
                assert.step('on_reverse_breadcrumb');
            }
        });
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.verifySteps(['on_reverse_breadcrumb']);

        webClient.destroy();
    });

    QUnit.test('handles "history_back" event', async function (assert) {
        assert.expect(2);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        await doAction(4);
        await doAction(3);
        webClient.env.bus.trigger('history-back');
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_control_panel .breadcrumb-item',
            "there should be one controller in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Partners Action 4',
            "breadcrumbs should display the display_name of the action");

        webClient.destroy();
    });

    QUnit.test('stores and restores scroll position', async function (assert) {
        assert.expect(5);

        var left = 0;
        var top = 0;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            webClient: {
                _getScrollPosition: function () {
                    return { top, left };
                },
                _scrollTo: function (to) {
                    assert.step('scrollTo left ' + to.left + ', top ' + to.top);
                },
            },
        });

        // execute a first action and simulate a scroll
        assert.step('execute action 3');
        await doAction(3);
        left = 50;
        top = 100;

        // execute a second action (in which we don't scroll)
        assert.step('execute action 4');
        await doAction(4);

        // go back using the breadcrumbs
        assert.step('go back to action 3');
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.verifySteps([
            'execute action 3',
            'execute action 4',
            'go back to action 3',
            'scrollTo left 50, top 100', // restore scroll position of action 3
        ]);

        webClient.destroy();
    });

    QUnit.test('executing an action with target != "new" closes all dialogs', async function (assert) {
        assert.expect(4);

        this.archs['partner,false,form'] = '<form>' +
                '<field name="o2m">' +
                    '<tree><field name="foo"/></tree>' +
                    '<form><field name="foo"/></form>' +
                '</field>' +
            '</form>';

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        await doAction(3);
        assert.containsOnce(webClient, '.o_list_view');

        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view');

        await testUtils.dom.click($(webClient.el).find('.o_form_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(document.body, '.modal .o_form_view');

        await doAction(1); // target != 'new'
        assert.containsNone(document.body, '.modal');

        webClient.destroy();
    });

    QUnit.test('executing an action with target "new" does not close dialogs', async function (assert) {
        assert.expect(4);

        this.archs['partner,false,form'] = '<form>' +
                '<field name="o2m">' +
                    '<tree><field name="foo"/></tree>' +
                    '<form><field name="foo"/></form>' +
                '</field>' +
            '</form>';

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        await doAction(3);
        assert.containsOnce(webClient, '.o_list_view');

        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view');

        await testUtils.dom.click($(webClient.el).find('.o_form_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(document.body, '.modal .o_form_view');

        await doAction(5); // target 'new'
        assert.containsN(document.body, '.modal .o_form_view', 2);

        webClient.destroy();
    });

    QUnit.test("rainbowman integrated to webClient", async function (assert) {
        assert.expect(10);
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            session: {
                show_effect: true,
            },
        });
        await doAction(1);
        assert.containsOnce(webClient, '.o_kanban_view');
        assert.containsNone(webClient, '.o_reward');
        webClient.env.bus.trigger('show-effect', {type: 'rainbow_man', fadeout: 'no'});
        await testUtils.nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_reward');
        assert.containsOnce(webClient, '.o_kanban_view');
        await testUtils.dom.click(webClient.el.querySelector('.o_kanban_record'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsNone(webClient, '.o_reward');
        assert.containsOnce(webClient, '.o_kanban_view');

        webClient.env.bus.trigger('show-effect', {type: 'rainbow_man', fadeout: 'no'});
        await testUtils.nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_reward');
        assert.containsOnce(webClient, '.o_kanban_view');

        // Do not force rainbow man to destroy on doAction
        // we let it die either after its animation or on user click
        await doAction(3);
        assert.containsOnce(webClient, '.o_reward');
        assert.containsOnce(webClient, '.o_list_view');

        webClient.destroy();
    });

    QUnit.test('show effect notification', async function (assert) {
        assert.expect(6);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            session: {
                show_effect: false,
            },
            services: {
                notification: NotificationService
            }
        });
        await doAction(1);
        assert.containsOnce(webClient, '.o_kanban_view');
        assert.containsNone(webClient, '.o_reward');
        assert.containsNone(document.querySelector('body'), '.o_notification');
        webClient.env.bus.trigger('show-effect', {type: 'rainbow_man', fadeout: 'no'});
        await testUtils.nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_kanban_view');
        assert.containsNone(webClient, '.o_reward');
        assert.containsOnce(document.querySelector('body'), '.o_notification');
        webClient.destroy();
    });

    QUnit.test('deconnection and reconnection notifications', async function (assert) {
        assert.expect(8);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            services: {
                notification: NotificationService
            }
        });
        await doAction(1);
        assert.containsOnce(webClient, '.o_kanban_view');
        assert.containsNone(document.querySelector('body'), '.o_notification');
        webClient.env.bus.trigger('connection_lost');
        await testUtils.nextTick();
        assert.containsOnce(document.querySelector('body'), '.o_notification');
        assert.strictEqual(
            document.querySelector('body .o_notification .o_notification_title').innerHTML,
            'Connection lost'
        );
        assert.containsOnce(webClient, '.o_kanban_view');

        webClient.env.bus.trigger('connection_restored');
        await testUtils.nextTick();
        assert.containsN(document.querySelector('body'), '.o_notification', 2);
        assert.strictEqual(
            document.querySelectorAll('body .o_notification .o_notification_title')[1].innerHTML,
            'Connection restored'
        );
        assert.containsOnce(webClient, '.o_kanban_view');
        webClient.destroy();
    });

    QUnit.test('display warning as notification', async function (assert) {
        assert.expect(6);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            services: {
                notification: NotificationService
            }
        });
        await doAction(1);
        assert.containsOnce(webClient, '.o_kanban_view');
        assert.containsNone(document.querySelector('body'), '.o_notification');
        webClient.trigger('warning', {title: 'gloria', message: 'Like to tell ya about my baby'});
        await testUtils.nextTick();
        assert.containsOnce(document.querySelector('body'), '.o_notification');
        assert.strictEqual(
            document.querySelector('body .o_notification .o_notification_title').innerHTML,
            'gloria'
        );
        assert.strictEqual(
            document.querySelector('body .o_notification .o_notification_content').innerHTML,
            'Like to tell ya about my baby'
        );
        assert.containsOnce(webClient, '.o_kanban_view');
        webClient.destroy();
    });

    QUnit.test('display warning as modal', async function (assert) {
        assert.expect(8);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            services: {
                notification: NotificationService
            }
        });
        await doAction(1);
        assert.containsOnce(webClient, '.o_kanban_view');
        assert.containsNone(document.querySelector('body'), '.modal');
        webClient.trigger('warning', {title: 'gloria', type: 'dialog', message: 'Like to tell ya about my baby'});
        await testUtils.nextTick();
        // In this case the bootstrap modal may take one more tick to be here
        await testUtils.nextTick();
        assert.containsOnce(document.querySelector('body'), '.modal');
        assert.strictEqual(
            document.querySelector('body .modal .modal-title').textContent,
            'gloria'
        );
        assert.strictEqual(
            document.querySelector('body .modal .modal-body').textContent.trim(),
            'Like to tell ya about my baby'
        );
        assert.containsOnce(webClient, '.o_kanban_view');
        await testUtils.dom.click(document.querySelector('body .modal .modal-footer button'));
        assert.containsOnce(webClient, '.o_kanban_view');
        assert.containsNone(document.querySelector('body'), '.modal');
        webClient.destroy();
    });

    QUnit.module('Push State');

    QUnit.test('properly push state', async function (assert) {
        assert.expect(3);

        var stateDescriptions = [
            {action: 4, model: "partner", title: "Partners Action 4", view_type: "kanban"},
            {action: 8, model: "pony", title: "Favorite Ponies", view_type: "list"},
            {action: 8, id: 4, model: "pony", title: "Twilight Sparkle", view_type: "form"},
        ];

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            webClient: {
                _updateState(state) {
                    var descr = stateDescriptions.shift();
                    assert.deepEqual(_.extend({}, state), descr,
                        "should notify the environment of new state");
                },
            },
        });
        await doAction(4);
        await doAction(8);
        await testUtils.dom.click($(webClient.el).find('tr.o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        webClient.destroy();
    });

    QUnit.test('push state after action is loaded, not before', async function (assert) {
        assert.expect(5);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            webClient: {
                _updateState: function () {
                    assert.step('push_state');
                },
            },
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(4);
        assert.verifySteps([
            '/web/action/load',
            '/web/dataset/call_kw/partner',
            '/web/dataset/search_read',
            'push_state'
        ]);

        webClient.destroy();
    });

    QUnit.test('do not push state for actions in target=new', async function (assert) {
        assert.expect(3);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            webClient: {
                _setWindowHash: function () {
                    assert.step('push_state');
                },
            },
        });
        await doAction(4);
        assert.verifySteps(['push_state']);
        await doAction(5);
        assert.verifySteps([]);

        webClient.destroy();
    });

    QUnit.test('do not push state when action fails', async function (assert) {
        assert.expect(4);

        let _hash = '';
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            webClient: {
                _setWindowHash(newHash) {
                    assert.step('push_state');
                    _hash = newHash;
                },
                _getWindowHash() {
                    return _hash;
                }
            },
            mockRPC: function (route, args) {
                if (args.method === 'read') {
                    // this is the rpc to load form view
                    return Promise.reject();
                }
                return this._super.apply(this, arguments);
            },
        });
        await doAction(8);
        assert.verifySteps(['push_state']);
        await testUtils.dom.click($(webClient.el).find('tr.o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.verifySteps([]);
        // we make sure here that the list view is still in the dom
        assert.containsOnce(webClient, '.o_list_view',
            "there should still be a list view in dom");

        webClient.destroy();
    });

    QUnit.module('Load State');

    QUnit.test('should not crash on invalid state', async function (assert) {
        assert.expect(2);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            webClient: {
                _getWindowHash() {
                    return '#res_model=partner'; // the valid key for the model is 'model', not 'res_model'
                }
            },
        });

        assert.strictEqual(webClient.el.querySelector('.o_action_manager').textContent, '',
            "should display nothing");
        assert.verifySteps([]);

        webClient.destroy();
    });

    QUnit.test('properly load client actions', async function (assert) {
        assert.expect(2);

        var ClientAction = AbstractAction.extend({
            start: function () {
                this.$el.text('Hello World');
                this.$el.addClass('o_client_action_test');
            },
        });
        core.action_registry.add('HelloWorldTest', ClientAction);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            webClient: {
                _getWindowHash() {
                    return '#action=HelloWorldTest';
                }
            }
        });

        assert.strictEqual($(webClient.el).find('.o_client_action_test').text(),
            'Hello World', "should have correctly rendered the client action");

        assert.verifySteps([]);

        webClient.destroy();
        delete core.action_registry.map.HelloWorldTest;
    });

    QUnit.test('properly load act window actions', async function (assert) {
        assert.expect(6);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            webClient: {
                _getWindowHash() {
                    return '#action=1';
                }
            }
        });

        assert.strictEqual($(webClient.el).find('.o_control_panel').length, 1,
            "should have rendered a control panel");
        assert.containsOnce(webClient, '.o_kanban_view',
            "should have rendered a kanban view");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read',
        ]);

        webClient.destroy();
    });

    QUnit.test('properly push state active_id', async function (assert) {
        assert.expect(13);

        Object.assign(this.archs, {
            // kanban views
            'partner,1,kanban': '<kanban><templates><t t-name="kanban-box">' +
                    '<div class="oe_kanban_global_click"><a name="1" type="action"></a><field name="foo"/></div>' +
                '</t></templates></kanban>',
        });

        let _hash = '#action=1';
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            webClient: {
                _getWindowHash() {
                    return _hash;
                },
                _setWindowHash(newHash) {
                    assert.step(newHash);
                    _hash = newHash;
                }
            }
        });
        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read',
            '#model=partner&view_type=kanban&action=1',
        ]);
        await testUtils.dom.click(webClient.el.querySelector('.o_kanban_record a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read',
            '#model=partner&view_type=kanban&action=1&active_id=1',
        ]);
        await testUtils.dom.click(webClient.el.querySelector('.breadcrumb-item'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.verifySteps([
            '/web/dataset/search_read',
            '#model=partner&view_type=kanban&action=1',
        ]);
        webClient.destroy();
    });

    QUnit.test('properly load records', async function (assert) {
        assert.expect(5);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            webClient: {
                _getWindowHash() {
                    return '#model=partner&id=2';
                }
            }
        });

        assert.containsOnce(webClient, '.o_form_view',
            "should have rendered a form view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Second record',
            "should have opened the second record");

        assert.verifySteps([
            'load_views',
            'read',
        ]);

        webClient.destroy();
    });

    QUnit.test('properly load default record', async function (assert) {
        assert.expect(5);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            webClient: {
                _getWindowHash() {
                    return '#action=3&id=&model=partner&view_type=form';
                }
            }
        });

        assert.containsOnce(webClient, '.o_form_view',
            "should have rendered a form view");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            'default_get',
        ]);

        webClient.destroy();
    });

    QUnit.test('load requested view for act window actions', async function (assert) {
        assert.expect(6);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            webClient: {
                _getWindowHash() {
                    return '#action=3&view_type=kanban';
                }
            }
        });

        assert.containsNone(webClient, '.o_list_view',
            "should not have rendered a list view");
        assert.containsOnce(webClient, '.o_kanban_view',
            "should have rendered a kanban view");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read',
        ]);

        webClient.destroy();
    });

    QUnit.test('lazy load multi record view if mono record one is requested', async function (assert) {
        assert.expect(11);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            webClient: {
                _getWindowHash() {
                    return '#action=3&id=2&view_type=form';
                }
            }
        });
        assert.containsNone(webClient, '.o_list_view',
            "should not have rendered a list view");
        assert.containsOnce(webClient, '.o_form_view',
            "should have rendered a form view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'Second record',
            "breadcrumbs should contain the display_name of the opened record");

        // go back to Lst
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_list_view',
            "should now display the list view");
        assert.containsNone(webClient, '.o_form_view',
            "should not display the form view anymore");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            'read', // read the opened record
            '/web/dataset/search_read', // search read when coming back to List
        ]);

        webClient.destroy();
    });

    QUnit.test('lazy load multi record view with previous action', async function (assert) {
        assert.expect(6);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(4);

        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb li').length, 1,
            "there should be one controller in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb li').text(), 'Partners Action 4',
            "breadcrumbs should contain the display_name of the opened record");

        await doAction(3, {
            resID: 2,
            viewType: 'form',
        });

        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb li').length, 3,
            "there should be three controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb li').text(), 'Partners Action 4PartnersSecond record',
            "the breadcrumb elements should be correctly ordered");

        // go back to List
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a:last'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb li').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb li').text(), 'Partners Action 4Partners',
            "the breadcrumb elements should be correctly ordered");

        webClient.destroy();
    });

    QUnit.test('lazy loaded multi record view with failing mono record one', async function (assert) {
        assert.expect(3);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                if (args.method === 'read') {
                    return Promise.reject();
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.actionManager.loadState(webClient, {
            action: 3,
            id: 2,
            view_type: 'form',
        });

        assert.containsNone(webClient, '.o_form_view');
        assert.containsNone(webClient, '.o_list_view');

        await doAction(1);

        assert.containsOnce(webClient, '.o_kanban_view');

        webClient.destroy();
    });

    QUnit.test('change the viewType of the current action', async function (assert) {
        assert.expect(13);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(3);

        assert.containsOnce(webClient, '.o_list_view',
            "should have rendered a list view");

        // switch to kanban view
        await testUtils.actionManager.loadState(webClient, {
            action: 3,
            view_type: 'kanban',
        });

        assert.containsNone(webClient, '.o_list_view',
            "should not display the list view anymore");
        assert.containsOnce(webClient, '.o_kanban_view',
            "should have switched to the kanban view");

        // switch to form view, open record 4
        await testUtils.actionManager.loadState(webClient, {
            action: 3,
            id: 4,
            view_type: 'form',
        });

        assert.containsNone(webClient, '.o_kanban_view',
            "should not display the kanban view anymore");
        assert.containsOnce(webClient, '.o_form_view',
            "should have switched to the form view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'Fourth record',
            "should have opened the requested record");

        // verify steps to ensure that the whole action hasn't been re-executed
        // (if it would have been, /web/action/load and load_views would appear
        // several times)
        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read', // list view
            '/web/dataset/search_read', // kanban view
            'read', // form view
        ]);

        webClient.destroy();
    });

    QUnit.test('change the id of the current action', async function (assert) {
        assert.expect(11);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });

        // execute action 3 and open the first record in a form view
        await doAction(3);
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_form_view',
            "should have rendered a form view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'First record',
            "should have opened the first record");

        // switch to record 4
        await testUtils.actionManager.loadState(webClient, {
            action: 3,
            id: 4,
            view_type: 'form',
        });

        assert.containsOnce(webClient, '.o_form_view',
            "should still display the form view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'Fourth record',
            "should have switched to the requested record");

        // verify steps to ensure that the whole action hasn't been re-executed
        // (if it would have been, /web/action/load and load_views would appear
        // twice)
        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read', // list view
            'read', // form view, record 1
            'read', // form view, record 4
        ]);

        webClient.destroy();
    });

    QUnit.test('should not load twice a loaded state', async function (assert) {
        // This test is historical, and has been roughly re-written when the
        // webclient/action manager have been converted to in Owl. It's purpose was
        // to ensure that, when loading a state from the url, that state wasn't
        // pushed back to the url when loaded, which would re-trigger a loading
        // of that exact same state, again, and again...
        assert.expect(6);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super(...arguments);
            },
            webClient: {
                _getWindowHash() {
                    return '#action=3';
                },
            },
        });

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read'
        ], "should load the action only once");

        await testUtils.dom.click($(webClient.el).find('tr.o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.verifySteps(['read'], "should correctly load the subsequent view");

        webClient.destroy();
    });

    QUnit.test('should not push a loaded state of a client action', async function (assert) {
        assert.expect(4);

        var ClientAction = AbstractAction.extend({
            init: function (parent, action, options) {
                this._super.apply(this, arguments);
                this.controllerID = options.controllerID;
            },
            start: function () {
                var self = this;
                var $button = $('<button>').text('Click Me!');
                $button.on('click', function () {
                    self.trigger_up('push_state', {
                        controllerID: self.controllerID,
                        state: {someValue: 'X'},
                    });
                });
                this.$el.append($button);
                return this._super.apply(this, arguments);
            },
        });
        core.action_registry.add('ClientAction', ClientAction);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            webClient: {
                _setWindowHash: function (newHash) {
                    assert.step('push_state');
                    assert.strictEqual(
                        newHash,
                        '#someValue=X&action=9'
                    );
                },
                _getWindowHash() {
                    return '#action=9';
                }
            },
        });

        assert.verifySteps([], "should not push the loaded state");

        await testUtils.dom.click($(webClient.el).find('button'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.verifySteps(['push_state'],
            "should push the state of it changes afterwards");

        webClient.destroy();
    });

    QUnit.test('change a param of an ir.actions.client in the url', async function (assert) {
        assert.expect(7);

        var ClientAction = AbstractAction.extend({
            hasControlPanel: true,
            init: function (parent, action) {
                this._super.apply(this, arguments);
                var context = action.context;
                this.a = context.params && context.params.a || 'default value';
            },
            start: function () {
                assert.step('start');
                this.$('.o_content').text(this.a);
                this.$el.addClass('o_client_action');
                this.trigger_up('push_state', {
                    controllerID: this.controllerID,
                    state: {a: this.a},
                });
                return this._super.apply(this, arguments);
            },
        });
        core.action_registry.add('ClientAction', ClientAction);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        // execute the client action
        await doAction(9);

        assert.strictEqual($(webClient.el).find('.o_client_action .o_content').text(), 'default value',
            "should have rendered the client action");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should be one controller in the breadcrumbs");

        // update param 'a' in the url
        await testUtils.actionManager.loadState(webClient, { action: 9, a: 'new value' });

        assert.strictEqual($(webClient.el).find('.o_client_action .o_content').text(), 'new value',
            "should have rerendered the client action with the correct param");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should still be one controller in the breadcrumbs");

        // should have executed the client action twice
        assert.verifySteps(['start', 'start']);

        webClient.destroy();
        delete core.action_registry.map.ClientAction;
    });

    QUnit.test('load a window action without id (in a multi-record view)', async function (assert) {
        assert.expect(14);

        var RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
            getItem() {
                assert.step('getItem');
                return this._super.apply(this, arguments);
            },
            setItem() {
                assert.step('setItem');
                this._super.apply(this, arguments);
            }
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            services: {
                session_storage: RamStorageService,
            },
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(4);

        assert.containsOnce(webClient, '.o_kanban_view',
            "should display a kanban view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Partners Action 4',
            "breadcrumbs should display the display_name of the action");

        await testUtils.actionManager.loadState(webClient, { model: 'partner', view_type: 'list' });

        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Partners Action 4',
            "should still be in the same action");
        assert.containsNone(webClient, '.o_kanban_view',
            "should no longer display a kanban view");
        assert.containsOnce(webClient, '.o_list_view',
            "should display a list view");

        assert.verifySteps([
            '/web/action/load', // action 3
            'load_views', // action 3
            '/web/dataset/search_read', // action 3
            'setItem', // action 3
            'getItem', // loadState
            'load_views', // loaded action
            '/web/dataset/search_read', // loaded action
            'setItem', // loaded action
        ]);

        webClient.destroy();
    });

    QUnit.test('load state supports being given menu_id alone', async function (assert) {
        assert.expect(6);

        const menus = {
            all_menu_ids: [666],
            children: [{
                id: 666,
                action: 'ir.actions.act_window,1',
                children: [],
            }]
        };
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: menus,
            mockRPC(route, args) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
            webClient: {
                _getWindowHash() {
                    return '#menu_id=666';
                }
            }
        });
        assert.containsOnce(webClient, '.o_kanban_view',
            "should display a kanban view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Partners Action 1',
            "breadcrumbs should display the display_name of the action");

        assert.verifySteps([
            '/web/action/load',
            '/web/dataset/call_kw/partner',
            '/web/dataset/search_read',
        ]);

        webClient.destroy();
    });

    QUnit.test('load state supports #home', async function (assert) {
        assert.expect(12);

        const menus = {
            all_menu_ids: [666],
            children: [{
                id: 666,
                action: 'ir.actions.act_window,1',
                children: [],
            }]
        };
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: menus,
            mockRPC(route, args) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
            webClient: {
                _getWindowHash() {
                    return '#action=3';
                }
            }
        });
        assert.containsOnce(webClient, '.o_list_view',
            "should display a list view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Partners',
            "breadcrumbs should display the display_name of the action");

        assert.verifySteps([
            '/web/action/load',
            '/web/dataset/call_kw/partner',
            '/web/dataset/search_read',
        ]);

        await testUtils.actionManager.loadState(webClient, {
            home: true,
        });
        assert.containsOnce(webClient, '.o_kanban_view',
            "should display a kanban view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Partners Action 1',
            "breadcrumbs should display the display_name of the action");
        assert.verifySteps([
            '/web/action/load',
            '/web/dataset/call_kw/partner',
            '/web/dataset/search_read',
        ]);
        webClient.destroy();
    });

    QUnit.test('load state supports #home as initial state', async function (assert) {
        assert.expect(6);

        const menus = {
            all_menu_ids: [666],
            children: [{
                id: 666,
                action: 'ir.actions.act_window,1',
                children: [],
            }]
        };
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: menus,
            mockRPC(route, args) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
            webClient: {
                _getWindowHash() {
                    return '#home';
                }
            }
        });
        assert.containsOnce(webClient, '.o_kanban_view',
            "should display a kanban view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Partners Action 1',
            "breadcrumbs should display the display_name of the action");
        assert.verifySteps([
            '/web/action/load',
            '/web/dataset/call_kw/partner',
            '/web/dataset/search_read',
        ]);
        webClient.destroy();
    });

    QUnit.test('load state different id null', async function (assert) {
        assert.expect(12);

        this.actions.push({
            id: 999,
            name: 'Partner',
            res_id: 2,
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'list'],[666, 'form']],
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC(route, args) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(999, {viewType: 'form'})
        assert.containsOnce(webClient, '.o_form_view');
        assert.containsN(webClient, '.breadcrumb-item', 2);
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item.active').text(), 'Second record');
        assert.verifySteps([
            '/web/action/load',
            '/web/dataset/call_kw/partner',
            '/web/dataset/call_kw/partner/read',
        ]);
        await loadState(webClient, {action:999, view_type: 'form'});
        assert.verifySteps([
             '/web/dataset/call_kw/partner/default_get',
        ]);
        assert.containsOnce(webClient, '.o_form_view.o_form_editable');
        assert.containsN(webClient, '.breadcrumb-item', 2);
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item.active').text(), 'New');
        webClient.destroy();
    });

    QUnit.module('Concurrency management');

    QUnit.test('drop previous actions if possible', async function (assert) {
        assert.expect(6);

        var def = testUtils.makeTestPromise();
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route) {
                var result = this._super.apply(this, arguments);
                assert.step(route);
                if (route === '/web/action/load') {
                    return def.then(_.constant(result));
                }
                return result;
            },
        });
        await doAction(4);
        await doAction(8);

        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        // action 4 loads a kanban view first, 6 loads a list view. We want a list
        assert.containsOnce(webClient, '.o_list_view');

        assert.verifySteps([
            '/web/action/load', // load action 4
            '/web/action/load', // load action 6
            '/web/dataset/call_kw/pony', // load views for action 6
            '/web/dataset/search_read', // search read for list view action 6
        ]);

        webClient.destroy();
    });

    QUnit.test('handle switching view and switching back on slow network', async function (assert) {
        assert.expect(8);

        var def = testUtils.makeTestPromise();
        var defs = [Promise.resolve(), def, Promise.resolve()];

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route) {
                assert.step(route);
                var result = this._super.apply(this, arguments);
                if (route === '/web/dataset/search_read') {
                    var def = defs.shift();
                    return def.then(_.constant(result));
                }
                return result;
            },
            debounce: false,
        });
        await doAction(4);

        // kanban view is loaded, switch to list view
        await testUtils.controlPanel.switchView(webClient, 'list');

        // here, list view is not ready yet, because def is not resolved
        // switch back to kanban view
        await testUtils.controlPanel.switchView(webClient, 'kanban');

        // here, we want the kanban view to reload itself, regardless of list view
        assert.verifySteps([
            "/web/action/load",             // initial load action
            "/web/dataset/call_kw/partner", // load views
            "/web/dataset/search_read",     // search_read for kanban view
            "/web/dataset/search_read",     // search_read for list view (not resolved yet)
            "/web/dataset/search_read"      // search_read for kanban view reload (not resolved yet)
        ]);

        // we resolve def => list view is now ready (but we want to ignore it)
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_kanban_view',
            "there should be a kanban view in dom");
        assert.containsNone(webClient, '.o_list_view',
            "there should not be a list view in dom");

        webClient.destroy();
    });

    QUnit.test('when an server action takes too much time...', async function (assert) {
        assert.expect(1);

        var def = testUtils.makeTestPromise();

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route) {
                if (route === '/web/action/run') {
                    return def.then(_.constant(1));
                }
                return this._super.apply(this, arguments);
            },
        });

        doAction(2);
        doAction(4);

        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item.active').text(), 'Partners Action 4',
            'action 4 should be loaded');

        webClient.destroy();
    });

    QUnit.test('clicking quickly on breadcrumbs...', async function (assert) {
        assert.expect(1);

        var def = Promise.resolve();

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'read') {
                    return def.then(_.constant(result));
                }
                return result;
            },
        });

        // create a situation with 3 breadcrumbs: kanban/form/list
        await doAction(4);
        await testUtils.dom.click($(webClient.el).find('.o_kanban_record:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        doAction(8);

        // now, the next read operations will be promise (this is the read
        // operation for the form view reload)
        def = testUtils.makeTestPromise();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        // click on the breadcrumbs for the form view, then on the kanban view
        // before the form view is fully reloaded
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb-item:eq(1)'));
        await testUtils.owlCompatibilityExtraNextTick();
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb-item:eq(0)'));
        await testUtils.owlCompatibilityExtraNextTick();

        // resolve the form view read
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item.active').text(), 'Partners Action 4',
            'action 4 should be loaded and visible');

        webClient.destroy();
    });

    QUnit.test('execute a new action while loading a lazy-loaded controller', async function (assert) {
        assert.expect(15);

        var def;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                assert.step(args.method || route);
                if (route === '/web/dataset/search_read' && args.model === 'partner') {
                    return Promise.resolve(def).then(_.constant(result));
                }
                return result;
            },
            webClient: {
                _getWindowHash() {
                    return "#action=3&id=2&view_type=form";
                },
            },
        });

        assert.containsOnce(webClient, '.o_form_view',
            "should display the form view of action 4");

        // click to go back to Kanban (this request is blocked)
        def = testUtils.makeTestPromise();
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_form_view',
        "should still display the form view of action 4");

        // execute another action meanwhile (don't block this request)
        await doAction(8, {clear_breadcrumbs: true});

        assert.containsOnce(webClient, '.o_list_view',
        "should display action 8");
        assert.containsNone(webClient, '.o_form_view',
        "should no longer display the form view");

        assert.verifySteps([
            '/web/action/load', // load state action 4
            'load_views', // load state action 4
            'read', // read the opened record (action 4)
            '/web/dataset/search_read', // blocked search read when coming back to Kanban (action 4)
            '/web/action/load', // action 8
            'load_views', // action 8
            '/web/dataset/search_read', // search read action 8
        ]);

        // unblock the switch to Kanban in action 4
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_list_view',
            "should still display action 8");
        assert.containsNone(webClient, '.o_kanban_view',
            "should not display the kanban view of action 4");

        assert.verifySteps([]);

        webClient.destroy();
    });

    QUnit.test('execute a new action while handling a call_button', async function (assert) {
        assert.expect(16);

        var self = this;
        var def = testUtils.makeTestPromise();
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === '/web/dataset/call_button') {
                    return def.then(_.constant(self.actions[0]));
                }
                return this._super.apply(this, arguments);
            },
        });

        // execute action 3 and open a record in form view
        await doAction(3);
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_form_view',
            "should display the form view of action 3");

        // click on 'Call method' button (this request is blocked)
        await testUtils.dom.click($(webClient.el).find('.o_form_view button:contains(Call method)'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_form_view',
            "should still display the form view of action 3");

        // execute another action
        await doAction(8, {clear_breadcrumbs: true});

        assert.containsOnce(webClient, '.o_list_view',
            "should display the list view of action 8");
        assert.containsNone(webClient, '.o_form_view',
            "should no longer display the form view");

        assert.verifySteps([
            '/web/action/load', // action 3
            'load_views', // action 3
            '/web/dataset/search_read', // list for action 3
            'read', // form for action 3
            'object', // click on 'Call method' button (this request is blocked)
            '/web/action/load', // action 8
            'load_views', // action 8
            '/web/dataset/search_read', // list for action 8
        ]);

        // unblock the call_button request
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_list_view',
            "should still display the list view of action 8");
        assert.containsNone(webClient, '.o_kanban_view',
            "should not display action 1");

        assert.verifySteps([]);

        webClient.destroy();
    });

    QUnit.test('execute a new action while switching to another controller', async function (assert) {
        assert.expect(15);

        var def;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                assert.step(args.method || route);
                if (args.method === 'read') {
                    return Promise.resolve(def).then(_.constant(result));
                }
                return result;
            },
        });

        await doAction(3);

        assert.containsOnce(webClient, '.o_list_view',
            "should display the list view of action 3");

        // switch to the form view (this request is blocked)
        def = testUtils.makeTestPromise();
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_list_view',
        "should still display the list view of action 3");

        // execute another action meanwhile (don't block this request)
        await doAction(4, {clear_breadcrumbs: true});

        assert.containsOnce(webClient, '.o_kanban_view',
            "should display the kanban view of action 8");
        assert.containsNone(webClient, '.o_list_view',
            "should no longer display the list view");

        assert.verifySteps([
            '/web/action/load', // action 3
            'load_views', // action 3
            '/web/dataset/search_read', // search read of list view of action 3
            'read', // read the opened record of action 3 (this request is blocked)
            '/web/action/load', // action 4
            'load_views', // action 4
            '/web/dataset/search_read', // search read action 4
        ]);

        // unblock the switch to the form view in action 3
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_kanban_view',
            "should still display the kanban view of action 8");
        assert.containsNone(webClient, '.o_form_view',
            "should not display the form view of action 3");

        assert.verifySteps([]);

        webClient.destroy();
    });

    QUnit.test('execute a new action while loading views', async function (assert) {
        assert.expect(10);

        var def;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                assert.step(args.method || route);
                if (args.method === 'load_views') {
                    return Promise.resolve(def).then(_.constant(result));
                }
                return result;
            },
        });

        // execute a first action (its 'load_views' RPC is blocked)
        def = testUtils.makeTestPromise();
        doAction(3);

        assert.containsNone(webClient, '.o_list_view',
            "should not display the list view of action 3");

        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        // execute another action meanwhile (and unlock the RPC)
        doAction(4);
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_kanban_view',
            "should display the kanban view of action 4");
        assert.containsNone(webClient, '.o_list_view',
            "should not display the list view of action 3");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should be one controller in the breadcrumbs");

        assert.verifySteps([
            '/web/action/load', // action 3
            'load_views', // action 3
            '/web/action/load', // action 4
            'load_views', // action 4
            '/web/dataset/search_read', // search read action 4
        ]);

        webClient.destroy();
    });

    QUnit.test('execute a new action while loading data of default view', async function (assert) {
        assert.expect(11);

        var def;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                assert.step(args.method || route);
                if (route === '/web/dataset/search_read') {
                    return Promise.resolve(def).then(_.constant(result));
                }
                return result;
            },
        });

        // execute a first action (its 'search_read' RPC is blocked)
        def = testUtils.makeTestPromise();
        doAction(3);

        assert.containsNone(webClient, '.o_list_view',
            "should not display the list view of action 3");

        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        // execute another action meanwhile (and unlock the RPC)
        doAction(4);
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_kanban_view',
            "should display the kanban view of action 4");
        assert.containsNone(webClient, '.o_list_view',
            "should not display the list view of action 3");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should be one controller in the breadcrumbs");

        assert.verifySteps([
            '/web/action/load', // action 3
            'load_views', // action 3
            '/web/dataset/search_read', // search read action 3
            '/web/action/load', // action 4
            'load_views', // action 4
            '/web/dataset/search_read', // search read action 4
        ]);

        webClient.destroy();
    });

    QUnit.test('open a record while reloading the list view', async function (assert) {
        assert.expect(12);

        var def;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route) {
                var result = this._super.apply(this, arguments);
                if (route === '/web/dataset/search_read') {
                    return Promise.resolve(def).then(_.constant(result));
                }
                return result;
            },
        });

        await doAction(3);

        assert.containsOnce(webClient, '.o_list_view',
            "should display the list view");
        assert.containsN(webClient, '.o_list_view .o_data_row', 5,
            "list view should contain 5 records");
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_list_buttons').length, 1,
            "list view buttons should be displayed in control panel");

        // reload (the search_read RPC will be blocked)
        def = testUtils.makeTestPromise();
        await testUtils.controlPanel.switchView(webClient, 'list');

        assert.containsN(webClient, '.o_list_view .o_data_row', 5,
            "list view should still contain 5 records");
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_list_buttons').length, 1,
            "list view buttons should still be displayed in control panel");

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_form_view',
            "should display the form view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_list_buttons').length, 0,
            "list view buttons should no longer be displayed in control panel");
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_form_buttons_view').length, 1,
            "form view buttons should be displayed instead");

        // unblock the search_read RPC
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_form_view',
            "should display the form view");
        assert.containsNone(webClient, '.o_list_view',
            "should not display the list view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_list_buttons').length, 0,
            "list view buttons should still not be displayed in control panel");
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_form_buttons_view').length, 1,
            "form view buttons should still be displayed instead");

        webClient.destroy();
    });

    QUnit.module('Client Actions');

    QUnit.test('can execute client actions from tag name', async function (assert) {
        assert.expect(2);

        var ClientAction = AbstractAction.extend({
            start: function () {
                this.$el.text('Hello World');
                this.$el.addClass('o_client_action_test');
            },
        });
        core.action_registry.add('HelloWorldTest', ClientAction);

        const webClient = await createWebClient({
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction('HelloWorldTest');

        assert.strictEqual(webClient.el.querySelector('.o_action_manager').innerHTML,
            '<div class="o_action o_client_action_test">Hello World</div>');
        assert.verifySteps([]);

        webClient.destroy();
        delete core.action_registry.map.HelloWorldTest;
    });

    QUnit.test('client action with control panel', async function (assert) {
        assert.expect(4);

        var ClientAction = AbstractAction.extend({
            hasControlPanel: true,
            start: async function () {
                this.$('.o_content').text('Hello World');
                this.$el.addClass('o_client_action_test');
                this.controlPanelProps.title = 'Hello';
                await this._super.apply(this, arguments);
            },
        });
        core.action_registry.add('HelloWorldTest', ClientAction);

        const webClient = await createWebClient();
        await doAction('HelloWorldTest');

        assert.strictEqual($(webClient.el).find('.o_control_panel:visible').length, 1,
            "should have rendered a control panel");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should be one controller in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Hello',
            "breadcrumbs should still display the title of the controller");
        assert.strictEqual($(webClient.el).find('.o_client_action_test .o_content').text(),
            'Hello World', "should have correctly rendered the client action");

        webClient.destroy();
        delete core.action_registry.map.HelloWorldTest;
    });

    QUnit.test('state is pushed for client actions', async function (assert) {
        assert.expect(3);

        const ClientAction = AbstractAction.extend({
            getTitle: function () {
                return 'a title';
            },
            getState: function () {
                return {foo: 'baz'};
            }
        });
        const webClient = await createWebClient({
            webClient: {
                _setWindowHash(hash) {
                    assert.step(`hash: ${hash}`);
                },
                _setWindowTitle(title) {
                    assert.step(`title: ${title}`);
                },
            },
        });
        core.action_registry.add('HelloWorldTest', ClientAction);

        await doAction('HelloWorldTest');

        assert.verifySteps([
            "hash: #foo=baz&action=HelloWorldTest",
            "title: a title",
        ]);
        webClient.destroy();
        delete core.action_registry.map.HelloWorldTest;
    });

    QUnit.test('breadcrumb is updated on title change', async function (assert) {
        assert.expect(2);

        var ClientAction = AbstractAction.extend({
            hasControlPanel: true,
            events: {
                click: function () {
                    this.updateControlPanel({ title: 'new title' });
                },
            },
            start: async function () {
                this.$('.o_content').text('Hello World');
                this.$el.addClass('o_client_action_test');
                this.controlPanelProps.title = 'initial title';
                await this._super.apply(this, arguments);
            },
        });
        const webClient = await createWebClient();
        core.action_registry.add('HelloWorldTest', ClientAction);
        await doAction('HelloWorldTest');

        assert.strictEqual($('ol.breadcrumb').text(), "initial title",
            "should have initial title as breadcrumb content");

        await testUtils.dom.click($(webClient.el).find('.o_client_action_test'));
        assert.strictEqual($('ol.breadcrumb').text(), "new title",
            "should have updated title as breadcrumb content");

        webClient.destroy();
        delete core.action_registry.map.HelloWorldTest;
    });

    QUnit.test('test display_notification client action', async function (assert) {
        assert.expect(6);

        testUtils.mock.patch(Notification, {
            _animation: false,
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            services: {
                notification: NotificationService,
            },
        });

        await doAction(1);
        assert.containsOnce(webClient, '.o_kanban_view');

        await doAction({
            type: 'ir.actions.client',
            tag: 'display_notification',
            params: {
                title: 'title',
                message: 'message',
                sticky: true,
            }
        });
        const notificationSelector = '.o_notification_manager .o_notification';

        assert.containsOnce(document.body, notificationSelector,
            'a notification should be present');

        const notificationElement = document.body.querySelector(notificationSelector);
        assert.strictEqual(
            notificationElement.querySelector('.o_notification_title').textContent,
            'title',
            "the notification should have the correct title"
        );
        assert.strictEqual(
            notificationElement.querySelector('.o_notification_content').textContent,
            'message',
            "the notification should have the correct message"
        );

        assert.containsOnce(webClient, '.o_kanban_view');

        await testUtils.dom.click(
            notificationElement.querySelector('.o_notification_close')
        );

        assert.containsNone(document.body, notificationSelector,
            "the notification should be destroy ");

        webClient.destroy();
        testUtils.mock.unpatch(Notification);
    });

    QUnit.module('Server actions');

    QUnit.test('can execute server actions from db ID', async function (assert) {
        assert.expect(9);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === '/web/action/run') {
                    assert.strictEqual(args.action_id, 2,
                        "should call the correct server action");
                    return Promise.resolve(1); // execute action 1
                }
                return this._super.apply(this, arguments);
            },
        });
        await doAction(2);

        assert.containsOnce(webClient, '.o_control_panel');
        assert.containsOnce(webClient, '.o_kanban_view');
        assert.verifySteps([
            '/web/action/load',
            '/web/action/run',
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read',
        ]);

        webClient.destroy();
    });

    QUnit.test('handle server actions returning false', async function (assert) {
        assert.expect(9);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === '/web/action/run') {
                    return Promise.resolve(false);
                }
                return this._super.apply(this, arguments);
            },
        });

        // execute an action in target="new"
        await doAction(5, {
            on_close: assert.step.bind(assert, 'close handler'),
        });
        assert.containsOnce(document.body, '.o_technical_modal .o_form_view');

        // execute a server action that returns false
        await doAction(2);
        assert.containsNone(document.body, '.o_technical_modal');
        assert.verifySteps([
            '/web/action/load', // action 5
            'load_views',
            'default_get',
            '/web/action/load', // action 2
            '/web/action/run',
            'close handler',
        ]);

        webClient.destroy();
    });

    QUnit.module('Report actions');

    QUnit.test('can execute report actions from db ID', async function (assert) {
        assert.expect(8);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            services: {
                blockUI: () => assert.step('blockUI'),
                report: ReportService,
                unblockUI: () => assert.step('unblockUI'),
            },
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === '/report/check_wkhtmltopdf') {
                    return Promise.resolve('ok');
                }
                return this._super.apply(this, arguments);
            },
            session: {
                get_file: async function (params) {
                    assert.step(params.url);
                    params.success();
                    params.complete();
                    return true;
                },
            },
        });
        await doAction(7,
            {
                on_close: function () {
                    assert.step('on_close');
                }
            },
            () => {
                    assert.step('action fully done'); // necessary to ensure reports are downloaded
            }
        );
        assert.verifySteps([
            '/web/action/load',
            '/report/check_wkhtmltopdf',
            'blockUI',
            '/report/download',
            'unblockUI',
            'on_close',
            'action fully done'
        ]);

        webClient.destroy();
    });

    QUnit.test('report actions can close modals and reload views', async function (assert) {
        assert.expect(12);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            services: {
                blockUI: () => assert.step('blockUI'),
                report: ReportService,
                unblockUI: () => assert.step('unblockUI'),
            },
            mockRPC: function (route) {
                if (route === '/report/check_wkhtmltopdf') {
                    return Promise.resolve('ok');
                }
                return this._super.apply(this, arguments);
            },
            session: {
                get_file: async function (params) {
                    assert.step(params.url);
                    params.success();
                    params.complete();
                    return true;
                },
            },
        });

        // load modal
        await doAction(5, {
            on_close: function () {
                assert.step('on_close');
            },
        });

        assert.strictEqual($('.o_technical_modal .o_form_view').length, 1,
        "should have rendered a form view in a modal");

        await doAction(7, {
            on_close: function () {
                assert.step('on_printed');
            },
        });

        assert.strictEqual($('.o_technical_modal .o_form_view').length, 1,
        "The modal should still exist");

        await doAction(11);

        assert.strictEqual($('.o_technical_modal .o_form_view').length, 0,
        "the modal should have been closed after the action report");

        assert.verifySteps([
            'blockUI',
            '/report/download',
            'unblockUI',
            'on_printed',
            'blockUI',
            '/report/download',
            'unblockUI',
            'on_close',
        ]);

        webClient.destroy();
    });

    QUnit.test('should trigger a notification if wkhtmltopdf is to upgrade', async function (assert) {
        assert.expect(7);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            services: {
                blockUI: () => assert.step('blockUI'),
                unblockUI: () => assert.step('unblockUI'),
                report: ReportService,
                notification: NotificationService.extend({
                    notify: () => assert.step('warning'),
                }),
            },
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === '/report/check_wkhtmltopdf') {
                    return Promise.resolve('upgrade');
                }
                return this._super.apply(this, arguments);
            },
            session: {
                get_file: async function (params) {
                    assert.step(params.url);
                    params.success();
                    params.complete();
                    return true;
                },
            },
        });
        await doAction(7);
        assert.verifySteps([
            '/web/action/load',
            '/report/check_wkhtmltopdf',
            'warning',
            'blockUI',
            '/report/download',
            'unblockUI',
        ]);

        webClient.destroy();
    });

    QUnit.test('should open the report client action if wkhtmltopdf is broken', async function (assert) {
        assert.expect(7);

        // patch the report client action to override its iframe's url so that
        // it doesn't trigger an RPC when it is appended to the DOM (for this
        // usecase, using removeSRCAttribute doesn't work as the RPC is
        // triggered as soon as the iframe is in the DOM, even if its src
        // attribute is removed right after)
        testUtils.mock.patch(ReportClientAction, {
            start: function () {
                var self = this;
                return this._super.apply(this, arguments).then(function () {
                    self._rpc({route: self.iframe.getAttribute('src')});
                    self.iframe.setAttribute('src', 'about:blank');
                });
            }
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            services: {
                report: ReportService,
                notification: NotificationService.extend({
                    notify: () => assert.step('warning'),
                })
            },
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === '/report/check_wkhtmltopdf') {
                    return Promise.resolve('broken');
                }
                if (route === '/report/html/some_report') {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
            session: {
                get_file: function (params) {
                    assert.step(params.url); // should not be called
                    return true;
                },
            },
        });
        await doAction(7);

        assert.containsOnce(webClient, '.o_report_iframe',
            "should have opened the report client action");
        assert.containsOnce(webClient, '.o_cp_buttons .o_report_buttons .o_report_print');

        assert.verifySteps([
            '/web/action/load',
            '/report/check_wkhtmltopdf',
            'warning',
            '/report/html/some_report', // report client action's iframe
        ]);

        webClient.destroy();
        testUtils.mock.unpatch(ReportClientAction);
    });

    QUnit.test('crashmanager service called on failed report download actions', async function (assert) {
        assert.expect(3);

        const webClient = await createWebClient({
            data: this.data,
            actions: this.actions,
            menus: this.menus,
            services: {
                blockUI: () => {},
                unblockUI: () => {},
                crash_manager: CrashManager.extend({
                    rpc_error: () => assert.step('rpc_error'),
                }),
                notification: NotificationService.extend({
                    notify: (params) => assert.step(`notification ${params.type}`),
                }),
                report: ReportService,
            },
            mockRPC: function (route) {
                if (route === '/report/check_wkhtmltopdf') {
                    return Promise.resolve('ok');
                }
                return this._super.apply(this, arguments);
            },
            session: {
                get_file: function (params) {
                    params.error({
                        data: {
                            name: 'error',
                            exception_type: 'warning',
                            arguments: ['could not download file'],
                        }
                    });
                    params.complete();
                },
            },
        });

        try {
            await doAction(11);
        } catch (e) {
            // e is undefined if we land here because of a rejected promise,
            // otherwise, it is an Error, which is not what we expect
            assert.strictEqual(e, undefined);
        }

        assert.verifySteps(['rpc_error', 'notification danger']);

        webClient.destroy();
    });

    QUnit.module('Window Actions');

    QUnit.test('can execute act_window actions from db ID', async function (assert) {
        assert.expect(6);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(1);

        assert.containsOnce(webClient, '.o_control_panel');
        assert.containsOnce(webClient, '.o_kanban_view');
        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read',
        ]);

        webClient.destroy();
    });

    QUnit.test('action menus are present in list view', async function (assert) {
        assert.expect(4);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                var res = this._super.apply(this, arguments);
                if (args.method === 'load_views') {
                    assert.strictEqual(args.kwargs.options.toolbar, true,
                        "should ask for toolbar information");
                    return res.then(function (fieldsViews) {
                        fieldsViews.list.toolbar = {
                            print: [{name: "Print that record"}],
                        };
                        return fieldsViews;
                    });
                }
                return res;
            },
        });
        await doAction(3);

        assert.containsNone(webClient, '.o_cp_action_menus');

        await testUtils.dom.clickFirst($(webClient.el).find('input.custom-control-input'));
        assert.isVisible($(webClient.el).find('.o_cp_action_menus button.o_dropdown_toggler_btn:contains("Print")'));
        assert.isVisible($(webClient.el).find('.o_cp_action_menus button.o_dropdown_toggler_btn:contains("Action")'));

        webClient.destroy();
    });

    QUnit.test('can switch between views', async function (assert) {
        assert.expect(18);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(3);

        assert.containsOnce(webClient, '.o_list_view',
            "should display the list view");

        // switch to kanban view
        await testUtils.controlPanel.switchView(webClient, 'kanban');
        assert.containsNone(webClient, '.o_list_view',
            "should no longer display the list view");
        assert.containsOnce(webClient, '.o_kanban_view',
            "should display the kanban view");

        // switch back to list view
        await testUtils.controlPanel.switchView(webClient, 'list');
        assert.containsOnce(webClient, '.o_list_view',
            "should display the list view");
        assert.containsNone(webClient, '.o_kanban_view',
            "should no longer display the kanban view");

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsNone(webClient, '.o_list_view',
            "should no longer display the list view");
        assert.containsOnce(webClient, '.o_form_view',
            "should display the form view");
        assert.strictEqual($(webClient.el).find('.o_field_widget[name=foo]').text(), 'yop',
            "should have opened the correct record");

        // go back to list view using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_list_view',
            "should display the list view");
        assert.containsNone(webClient, '.o_form_view',
            "should no longer display the form view");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read', // list
            '/web/dataset/search_read', // kanban
            '/web/dataset/search_read', // list
            'read', // form
            '/web/dataset/search_read', // list
        ]);

        webClient.destroy();
    });

    QUnit.test('orderedBy in context is not propagated when executing another action', async function (assert) {
        assert.expect(6);

        this.data.partner.fields.foo.sortable = true;

        this.archs['partner,false,form'] = `
            <header>
                <button name="8" string="Execute action" type="action"/>
            </header>`;

        var searchReadCount = 1;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    if (searchReadCount === 1) {
                        assert.strictEqual(args.model, 'partner');
                        assert.notOk(args.sort);
                    }
                    if (searchReadCount === 2) {
                        assert.strictEqual(args.model, 'partner');
                        assert.strictEqual(args.sort, "foo ASC");
                    }
                    if (searchReadCount === 3) {
                        assert.strictEqual(args.model, 'pony');
                        assert.notOk(args.sort);
                    }
                    searchReadCount += 1;
                }
                return this._super.apply(this, arguments);
            },
        });
        await doAction(3);

        // Simulate the activation of a filter
        var searchData = {
            domains: [[["foo", "=", "yop"]]],
            contexts: [{
                orderedBy: [],
            }],
        };
        webClient.trigger('search', searchData);

        // Sort records
        await testUtils.dom.click($(webClient.el).find('.o_list_view th.o_column_sortable'));
        await testUtils.owlCompatibilityExtraNextTick();

        // get to the form view of the model, on the first record
        await testUtils.dom.click($(webClient.el).find('.o_data_cell:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        // Change model by clicking on the button within the form
        await testUtils.dom.click($(webClient.el).find('.o_form_view button'));
        await testUtils.owlCompatibilityExtraNextTick();

        webClient.destroy();
    });

    QUnit.test('breadcrumbs are updated when switching between views', async function (assert) {
        assert.expect(16);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(3);

        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should be one controller in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Partners',
            "breadcrumbs should display the display_name of the action");

        // switch to kanban view
        await testUtils.controlPanel.switchView(webClient, 'kanban');
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should still be one controller in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Partners',
            "breadcrumbs should still display the display_name of the action");

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_kanban_view .o_kanban_record:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'First record',
            "breadcrumbs should contain the display_name of the opened record");

        // go back to kanban view using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_kanban_view', "should be back on kanban view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should be one controller in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Partners',
            "breadcrumbs should display the display_name of the action");

        // switch back to list view
        await testUtils.controlPanel.switchView(webClient, 'list');
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should still be one controller in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Partners',
            "breadcrumbs should still display the display_name of the action");

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'First record',
            "breadcrumbs should contain the display_name of the opened record");

        // go back to list view using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_list_view', "should be back on list view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should be one controller in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(), 'Partners',
            "breadcrumbs should display the display_name of the action");

        webClient.destroy();
    });

    QUnit.test('switch buttons are updated when switching between views', async function (assert) {
        assert.expect(13);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(3);

        assert.containsN(webClient, '.o_control_panel button.o_switch_view', 2,
            "should have two switch buttons (list and kanban)");
        assert.containsOnce(webClient, '.o_control_panel button.o_switch_view.active',
            "should have only one active button");
        assert.hasClass($(webClient.el).find('.o_control_panel .o_switch_view:first'), 'o_list',
            "list switch button should be the first one");
        assert.hasClass($(webClient.el).find('.o_control_panel .o_switch_view.o_list'), 'active',
            "list should be the active view");

        // switch to kanban view
        await testUtils.controlPanel.switchView(webClient, 'kanban');
        assert.containsN(webClient, '.o_control_panel .o_switch_view', 2,
            "should still have two switch buttons (list and kanban)");
        assert.containsOnce(webClient, '.o_control_panel .o_switch_view.active',
            "should still have only one active button");
        assert.hasClass($(webClient.el).find('.o_control_panel .o_switch_view:first'), 'o_list',
            "list switch button should still be the first one");
        assert.hasClass($(webClient.el).find('.o_control_panel .o_switch_view.o_kanban'), 'active',
            "kanban should now be the active view");

        // switch back to list view
        await testUtils.controlPanel.switchView(webClient, 'list');
        assert.containsN(webClient, '.o_control_panel .o_switch_view', 2,
            "should still have two switch buttons (list and kanban)");
        assert.hasClass($(webClient.el).find('.o_control_panel .o_switch_view.o_list'), 'active',
            "list should now be the active view");

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsNone(webClient, '.o_control_panel .o_switch_view',
            "should not have any switch buttons");

        // go back to list view using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsN(webClient, '.o_control_panel .o_switch_view', 2,
            "should have two switch buttons (list and kanban)");
        assert.hasClass($(webClient.el).find('.o_control_panel .o_switch_view.o_list'), 'active',
            "list should be the active view");

        webClient.destroy();
    });

    QUnit.test('pager is updated when switching between views', async function (assert) {
        assert.expect(10);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(4);

        assert.strictEqual($(webClient.el).find('.o_control_panel .o_pager_value').text(), '1-5',
            "value should be correct for kanban");
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_pager_limit').text(), '5',
            "limit should be correct for kanban");

        // switch to list view
        await testUtils.controlPanel.switchView(webClient, 'list');
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_pager_value').text(), '1-3',
            "value should be correct for list");
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_pager_limit').text(), '5',
            "limit should be correct for list");

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_pager_value').text(), '1',
            "value should be correct for form");
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_pager_limit').text(), '3',
            "limit should be correct for form");

        // go back to list view using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_pager_value').text(), '1-3',
            "value should be correct for list");
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_pager_limit').text(), '5',
            "limit should be correct for list");

        // switch back to kanban view
        await testUtils.controlPanel.switchView(webClient, 'kanban');
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_pager_value').text(), '1-5',
            "value should be correct for kanban");
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_pager_limit').text(), '5',
            "limit should be correct for kanban");

        webClient.destroy();
    });

    QUnit.test("domain is kept when switching between views", async function (assert) {
        assert.expect(5);

        this.actions[2].search_view_id = [1, 'a custom search view'];

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        await doAction(3);
        assert.containsN(webClient, '.o_data_row', 5);

        // activate a domain
        await cpHelpers.toggleFilterMenu(webClient);
        await cpHelpers.toggleMenuItem(webClient, "Bar");
        assert.containsN(webClient, '.o_data_row', 2);

        // switch to kanban
        await testUtils.controlPanel.switchView(webClient, 'kanban');
        assert.containsN(webClient, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        // remove the domain
        await testUtils.dom.click($(webClient.el).find('.o_searchview .o_facet_remove'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsN(webClient, '.o_kanban_record:not(.o_kanban_ghost)', 5);

        // switch back to list
        await testUtils.controlPanel.switchView(webClient, 'list');
        assert.containsN(webClient, '.o_data_row', 5);

        webClient.destroy();
    });

    QUnit.test('there is no flickering when switching between views', async function (assert) {
        assert.expect(20);

        var def;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function () {
                var result = this._super.apply(this, arguments);
                return Promise.resolve(def).then(_.constant(result));
            },
        });
        await doAction(3);

        // switch to kanban view
        def = testUtils.makeTestPromise();
        await testUtils.controlPanel.switchView(webClient, 'kanban');
        assert.containsOnce(webClient, '.o_list_view',
            "should still display the list view");
        assert.containsNone(webClient, '.o_kanban_view',
            "shouldn't display the kanban view yet");
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsNone(webClient, '.o_list_view',
            "shouldn't display the list view anymore");
        assert.containsOnce(webClient, '.o_kanban_view',
            "should now display the kanban view");

        // switch back to list view
        def = testUtils.makeTestPromise();
        await testUtils.controlPanel.switchView(webClient, 'list');
        assert.containsOnce(webClient, '.o_kanban_view',
            "should still display the kanban view");
        assert.containsNone(webClient, '.o_list_view',
            "shouldn't display the list view yet");
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsNone(webClient, '.o_kanban_view',
            "shouldn't display the kanban view anymore");
        assert.containsOnce(webClient, '.o_list_view',
            "should now display the list view");

        // open a record in form view
        def = testUtils.makeTestPromise();
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_list_view',
            "should still display the list view");
        assert.containsNone(webClient, '.o_form_view',
            "shouldn't display the form view yet");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should still be one controller in the breadcrumbs");
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsNone(webClient, '.o_list_view',
            "should no longer display the list view");
        assert.containsOnce(webClient, '.o_form_view',
            "should display the form view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should be two controllers in the breadcrumbs");

        // go back to list view using the breadcrumbs
        def = testUtils.makeTestPromise();
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view',
            "should still display the form view");
        assert.containsNone(webClient, '.o_list_view',
            "shouldn't display the list view yet");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should still be two controllers in the breadcrumbs");
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsNone(webClient, '.o_form_view',
            "should no longer display the form view");
        assert.containsOnce(webClient, '.o_list_view',
            "should display the list view");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should be one controller in the breadcrumbs");

        webClient.destroy();
    });

    QUnit.test('breadcrumbs are updated when display_name changes', async function (assert) {
        assert.expect(4);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(3);

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'First record',
            "breadcrumbs should contain the display_name of the opened record");

        // switch to edit mode and change the display_name
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .o_form_button_edit'));
        await testUtils.fields.editInput($(webClient.el).find('.o_field_widget[name=display_name]'), 'New name');
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .o_form_button_save'));

        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should still be two controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'New name',
            "breadcrumbs should contain the display_name of the opened record");

        webClient.destroy();
    });

    QUnit.test('reverse breadcrumb works on accesskey "b"', async function (assert) {
        assert.expect(4);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(3);

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        await testUtils.dom.click($(webClient.el).find('.o_form_view button:contains(Execute action)'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsN(webClient, '.o_control_panel .breadcrumb li', 3);

        let $previousBreadcrumb = $(webClient.el).find('.o_control_panel .breadcrumb li.active').prev();
        assert.strictEqual($previousBreadcrumb.attr("accesskey"), "b",
            "previous breadcrumb should have accessKey 'b'");
        await testUtils.dom.click($previousBreadcrumb);
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsN(webClient, '.o_control_panel .breadcrumb li', 2);

        $previousBreadcrumb = $(webClient.el).find('.o_control_panel .breadcrumb li.active').prev();
        assert.strictEqual($previousBreadcrumb.attr("accesskey"), "b",
            "previous breadcrumb should have accessKey 'b'");

        webClient.destroy();
    });

    QUnit.test('reload previous controller when discarding a new record', async function (assert) {
        assert.expect(8);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(3);

        // create a new record
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .o_list_button_add'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view.o_form_editable',
            "should have opened the form view in edit mode");

        // discard
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .o_form_button_cancel'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_list_view',
            "should have switched back to the list view");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read', // list
            'default_get', // form
            '/web/dataset/search_read', // list
        ]);

        webClient.destroy();
    });

    QUnit.test('requests for execute_action of type object are handled', async function (assert) {
        assert.expect(10);

        var self = this;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === '/web/dataset/call_button') {
                    assert.deepEqual(args, {
                        args: [[1]],
                        kwargs: {context: {some_key: 2}},
                        method: 'object',
                        model: 'partner',
                    }, "should call route with correct arguments");
                    var record = _.findWhere(self.data.partner.records, {id: args.args[0][0]});
                    record.foo = 'value changed';
                    return Promise.resolve(false);
                }
                return this._super.apply(this, arguments);
            },
            session: {user_context: {
                some_key: 2,
            }},
        });
        await doAction(3);

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_field_widget[name=foo]').text(), 'yop',
            "check initial value of 'yop' field");

        // click on 'Call method' button (should call an Object method)
        await testUtils.dom.click($(webClient.el).find('.o_form_view button:contains(Call method)'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_field_widget[name=foo]').text(), 'value changed',
            "'yop' has been changed by the server, and should be updated in the UI");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read', // list for action 3
            'read', // form for action 3
            'object', // click on 'Call method' button
            'read', // re-read form view
        ]);

        webClient.destroy();
    });

    QUnit.test('requests for execute_action of type action are handled', async function (assert) {
        assert.expect(11);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(3);

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        // click on 'Execute action' button (should execute an action)
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should be two parts in the breadcrumbs");
        await testUtils.dom.click($(webClient.el).find('.o_form_view button:contains(Execute action)'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 3,
            "the returned action should have been stacked over the previous one");
        assert.containsOnce(webClient, '.o_kanban_view',
            "the returned action should have been executed");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read', // list for action 3
            'read', // form for action 3
            '/web/action/load', // click on 'Execute action' button
            'load_views',
            '/web/dataset/search_read', // kanban for action 4
        ]);

        webClient.destroy();
    });

    QUnit.test('requests for execute_action of type object: disable buttons', async function (assert) {
        assert.expect(2);

        var def;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_button') {
                    return Promise.resolve(false);
                } else if (args.method === 'read') {
                    // Block the 'read' call
                    var result = this._super.apply(this, arguments);
                    return Promise.resolve(def).then(_.constant(result));
                }
                return this._super.apply(this, arguments);
            },
        });
        await doAction(3);

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        // click on 'Call method' button (should call an Object method)
        def = testUtils.makeTestPromise();
        await testUtils.dom.click($(webClient.el).find('.o_form_view button:contains(Call method)'));
        await testUtils.owlCompatibilityExtraNextTick();

        // Buttons should be disabled
        assert.strictEqual(
            $(webClient.el).find('.o_form_view button:contains(Call method)').attr('disabled'),
            'disabled', 'buttons should be disabled');

        // Release the 'read' call
        def.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        // Buttons should be enabled after the reload
        assert.strictEqual(
            $(webClient.el).find('.o_form_view button:contains(Call method)').attr('disabled'),
            undefined, 'buttons should be disabled');

        webClient.destroy();
    });

    QUnit.test('requests for execute_action of type object: disable buttons (2)', async function (assert) {
        assert.expect(6);

        this.archs['pony,44,form'] = `
            <form>
                <field name="name"/>
                <button string="Cancel" class="cancel-btn" special="cancel"/>
            </form>`;
        this.actions[3] = {
            id: 4,
            name: 'Create a Partner',
            res_model: 'pony',
            target: 'new',
            type: 'ir.actions.act_window',
            views: [[44, 'form']],
        };
        var def = testUtils.makeTestPromise();
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                const result = this._super.apply(this, arguments);
                if (args.method === 'default_get') {
                    // delay the opening of the dialog
                    return Promise.resolve(def).then(() => result);
                }
                return result;
            },
        });
        await doAction(3);
        assert.containsOnce(webClient, '.o_list_view');

        // open first record in form view
        await testUtils.dom.click(webClient.el.querySelector('.o_list_view .o_data_row'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view');

        // click on 'Execute action', to execute action 4 in a dialog
        await testUtils.dom.click(webClient.el.querySelector('.o_form_view button[name="4"]'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.ok(webClient.el.querySelector('.o_cp_buttons .o_form_button_edit').disabled,
            'control panel buttons should be disabled');

        def.resolve();
        await testUtils.nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.modal .o_form_view');
        assert.notOk(webClient.el.querySelector('.o_cp_buttons .o_form_button_edit').disabled,
            'control panel buttons should have been re-enabled');

        await testUtils.dom.click(webClient.el.querySelector('.modal .cancel-btn'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.notOk(webClient.el.querySelector('.o_cp_buttons .o_form_button_edit').disabled,
            'control panel buttons should still be enabled');

        webClient.destroy();
    });

    QUnit.test('can open different records from a multi record view', async function (assert) {
        assert.expect(11);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(3);

        // open the first record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'First record',
            "breadcrumbs should contain the display_name of the opened record");
        assert.strictEqual($(webClient.el).find('.o_field_widget[name=foo]').text(), 'yop',
            "should have opened the correct record");

        // go back to list view using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await testUtils.owlCompatibilityExtraNextTick();

        // open the second record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:nth(1)'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'Second record',
            "breadcrumbs should contain the display_name of the opened record");
        assert.strictEqual($(webClient.el).find('.o_field_widget[name=foo]').text(), 'blip',
            "should have opened the correct record");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read', // list
            'read', // form
            '/web/dataset/search_read', // list
            'read', // form
        ]);

        webClient.destroy();
    });

    QUnit.test('restore previous view state when switching back', async function (assert) {
        assert.expect(5);

        this.actions[2].views.unshift([false, 'graph']);
        this.archs['partner,false,graph'] = '<graph></graph>';

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(3);

        assert.hasClass($(webClient.el).find('.o_control_panel  .fa-bar-chart-o'), 'active',
            "bar chart button is active");
        assert.doesNotHaveClass($(webClient.el).find('.o_control_panel  .fa-area-chart'), 'active',
            "line chart button is not active");

        // display line chart
        await testUtils.dom.click($(webClient.el).find('.o_control_panel  .fa-area-chart'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.hasClass($(webClient.el).find('.o_control_panel  .fa-area-chart'), 'active',
            "line chart button is now active");

        // switch to kanban and back to graph view
        await testUtils.controlPanel.switchView(webClient, 'kanban');
        assert.strictEqual($(webClient.el).find('.o_control_panel  .fa-area-chart').length, 0,
            "graph buttons are no longer in control panel");

        await testUtils.controlPanel.switchView(webClient, 'graph');
        assert.hasClass($(webClient.el).find('.o_control_panel  .fa-area-chart'), 'active',
            "line chart button is still active");

        webClient.destroy();
    });

    QUnit.test('view switcher is properly highlighted in graph view', async function (assert) {
        assert.expect(4);

        // note: this test should be moved to graph tests ?

        this.actions[2].views.splice(1, 1, [false, 'graph']);
        this.archs['partner,false,graph'] = '<graph></graph>';

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(3);

        assert.hasClass($(webClient.el).find('.o_control_panel .o_switch_view.o_list'), 'active',
            "list button in control panel is active");
        assert.doesNotHaveClass($(webClient.el).find('.o_control_panel .o_switch_view.o_graph'), 'active',
            "graph button in control panel is not active");

        // switch to graph view
        await testUtils.controlPanel.switchView(webClient, 'graph');
        assert.doesNotHaveClass($(webClient.el).find('.o_control_panel .o_switch_view.o_list'), 'active',
            "list button in control panel is not active");
        assert.hasClass($(webClient.el).find('.o_control_panel .o_switch_view.o_graph'), 'active',
            "graph button in control panel is active");

        webClient.destroy();
    });

    QUnit.test('can interact with search view', async function (assert) {
        assert.expect(2);

        this.archs['partner,false,search'] = `
            <search>
                <group>
                    <filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
                </group>
            </search>`;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(3);

        assert.doesNotHaveClass($(webClient.el).find('.o_list_table'), 'o_list_table_grouped',
            "list view is not grouped");

        // open group by dropdown
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .o_cp_right button:contains(Group By)'));

        // click on first link
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .o_group_by_menu a:first'));

        assert.hasClass($(webClient.el).find('.o_list_table'), 'o_list_table_grouped',
            'list view is now grouped');

        webClient.destroy();
    });

    QUnit.test('can open a many2one external window', async function (assert) {
        // AAB: this test could be merged with 'many2ones in form views' in relational_fields_tests.js
        assert.expect(8);

        this.data.partner.records[0].bar = 2;
        this.archs['partner,false,search'] = `
            <search>
                <group>
                    <filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
                </group>
            </search>`;
        this.archs['partner,false,form'] = `
            <form>
                <group>
                    <field name="foo"/>
                    <field name="bar"/>
                </group>
            </form>`;

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(route);
                if (args.method === "get_formview_id") {
                    return Promise.resolve(false);
                }
                return this._super.apply(this, arguments);
            },
        });
        await doAction(3);

        // open first record in form view
        await testUtils.dom.click($(webClient.el).find('.o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        // click on edit
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .o_form_button_edit'));

        // click on external button for m2o
        await testUtils.dom.click($(webClient.el).find('.o_external_button'));

        assert.verifySteps([
            '/web/action/load',             // initial load action
            '/web/dataset/call_kw/partner', // load views
            '/web/dataset/search_read',     // read list view data
            '/web/dataset/call_kw/partner/read', // read form view data
            '/web/dataset/call_kw/partner/get_formview_id', // get form view id
            '/web/dataset/call_kw/partner', // load form view for modal
            '/web/dataset/call_kw/partner/read' // read data for m2o record
        ]);
        webClient.destroy();
    });

    QUnit.test('ask for confirmation when leaving a "dirty" view', async function (assert) {
        assert.expect(4);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(4);

        // open record in form view
        await testUtils.dom.click($(webClient.el).find('.o_kanban_record:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        // edit record
        await testUtils.dom.click($(webClient.el).find('.o_control_panel button.o_form_button_edit'));
        await testUtils.fields.editInput($(webClient.el).find('input[name="foo"]'), 'pinkypie');

        // go back to kanban view
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb-item:first a'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.strictEqual($('.modal .modal-body').text(),
            "The record has been modified, your changes will be discarded. Do you want to proceed?",
            "should display a modal dialog to confirm discard action");

        // cancel
        await testUtils.dom.click($('.modal .modal-footer button.btn-secondary'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_form_view',
            "should still be in form view");

        // go back again to kanban view
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb-item:first a'));
        await testUtils.owlCompatibilityExtraNextTick();

        // confirm discard
        await testUtils.dom.click($('.modal .modal-footer button.btn-primary'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsNone(webClient, '.o_form_view',
            "should no longer be in form view");
        assert.containsOnce(webClient, '.o_kanban_view',
            "should be in kanban view");

        webClient.destroy();
    });

    QUnit.test('limit set in action is passed to each created controller', async function (assert) {
        assert.expect(2);

        _.findWhere(this.actions, {id: 3}).limit = 2;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(3);

        assert.containsN(webClient, '.o_data_row', 2,
            "should only display 2 record");

        // switch to kanban view
        await testUtils.controlPanel.switchView(webClient, 'kanban');

        assert.strictEqual($(webClient.el).find('.o_kanban_record:not(.o_kanban_ghost)').length, 2,
            "should only display 2 record");

        webClient.destroy();
    });

    QUnit.test('go back to a previous action using the breadcrumbs', async function (assert) {
        assert.expect(10);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(3);

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'First record',
            "breadcrumbs should contain the display_name of the opened record");

        // push another action on top of the first one, and come back to the form view
        await doAction(4);
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 3,
            "there should be three controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'Partners Action 4',
            "breadcrumbs should contain the name of the current action");

        // go back using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a:nth(1)'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'First record',
            "breadcrumbs should contain the display_name of the opened record");

        // push again the other action on top of the first one, and come back to the list view
        await doAction(4);
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 3,
            "there should be three controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'Partners Action 4',
            "breadcrumbs should contain the name of the current action");

        // go back using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 1,
            "there should be one controller in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'Partners',
            "breadcrumbs should contain the name of the current action");

        webClient.destroy();
    });

    QUnit.test('form views are restored in readonly when coming back in breadcrumbs', async function (assert) {
        assert.expect(2);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(3);

        // open a record in form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        // switch to edit mode
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .o_form_button_edit'));

        assert.hasClass($(webClient.el).find('.o_form_view'), 'o_form_editable');
        // do some other action
        await doAction(4);
        // go back to form view
        await testUtils.dom.clickLast($(webClient.el).find('.o_control_panel .breadcrumb a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.hasClass($(webClient.el).find('.o_form_view'), 'o_form_readonly');

        webClient.destroy();
    });

    QUnit.test('honor group_by specified in actions context', async function (assert) {
        assert.expect(5);

        _.findWhere(this.actions, {id: 3}).context = "{'group_by': 'bar'}";
        this.archs['partner,false,search'] = `
            <search>
                <group>
                    <filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
                </group>
            </search>`;

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(3);

        assert.containsOnce(webClient, '.o_list_table_grouped',
            "should be grouped");
        assert.containsN(webClient, '.o_group_header', 2,
            "should be grouped by 'bar' (two groups) at first load");

        // groupby 'bar' using the searchview
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .o_cp_right button:contains(Group By)'));
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .o_group_by_menu a:first'));

        assert.containsN(webClient, '.o_group_header', 5,
            "should be grouped by 'foo' (five groups)");

        // remove the groupby in the searchview
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .o_searchview .o_facet_remove'));

        assert.containsOnce(webClient, '.o_list_table_grouped',
            "should still be grouped");
        assert.containsN(webClient, '.o_group_header', 2,
            "should be grouped by 'bar' (two groups) at reload");

        webClient.destroy();
    });

    QUnit.test('switch request to unknown view type', async function (assert) {
        assert.expect(7);

        this.actions.push({
            id: 33,
            name: 'Partners',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'list'], [1, 'kanban']], // no form view
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(33);

        assert.containsOnce(webClient, '.o_list_view',
            "should display the list view");

        // try to open a record in a form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_list_view',
            "should still display the list view");
        assert.containsNone(webClient, '.o_form_view',
            "should not display the form view");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read',
        ]);

        webClient.destroy();
    });

    QUnit.test('save current search', async function (assert) {
        assert.expect(4);

        testUtils.mock.patch(ListController, {
            getOwnedQueryParams: function () {
                return {
                    context: {
                        shouldBeInFilterContext: true,
                    }
                };
            },
        });

        this.actions.push({
            id: 33,
            context: {
                shouldNotBeInFilterContext: false,
            },
            name: 'Partners',
            res_model: 'partner',
            search_view_id: [1, 'a custom search view'],
            type: 'ir.actions.act_window',
            views: [[false, 'list']],
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            dataManager: {
                create_filter: function (filter) {
                    assert.strictEqual(filter.domain, `[("bar", "=", 1)]`,
                        "should save the correct domain");
                    const expectedContext = {
                        group_by: [], // default groupby is an empty list
                        shouldBeInFilterContext: true,
                    };
                    assert.deepEqual(filter.context, expectedContext,
                        "should save the correct context");
                },
            },
        });
        await doAction(33);

        assert.containsN(webClient, '.o_data_row', 5,
            "should contain 5 records");

        // filter on bar
        await cpHelpers.toggleFilterMenu(webClient);
        await cpHelpers.toggleMenuItem(webClient, "Bar");

        assert.containsN(webClient, '.o_data_row', 2);

        // save filter
        await cpHelpers.toggleFavoriteMenu(webClient);
        await cpHelpers.toggleSaveFavorite(webClient);
        await cpHelpers.editFavoriteName(webClient, "some name");
        await cpHelpers.saveFavorite(webClient);

        testUtils.mock.unpatch(ListController);
        webClient.destroy();
    });

    QUnit.test('execute smart button and back', async function (assert) {
        assert.expect(8);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            webClient: {
                _getWindowHash() {
                    return '#action=24';
                }
            },
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.notOk('default_partner' in args.kwargs.context);
                }
                if (route === '/web/dataset/search_read') {
                    assert.strictEqual(args.context.default_partner, 2);
                }
                return this._super.apply(this, arguments);
            }
        });
        assert.containsOnce(webClient, '.o_form_view');
        assert.containsN(webClient, '.o_form_buttons_view button:not([disabled])', 2);

        await testUtils.dom.click(webClient.el.querySelector('.oe_stat_button'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_kanban_view');

        await testUtils.dom.click(webClient.el.querySelector('.breadcrumb-item'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view');
        assert.containsN(webClient, '.o_form_buttons_view button:not([disabled])', 2);
        webClient.destroy();
    });

    QUnit.test('execute smart button and fails', async function (assert) {
        assert.expect(11);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            webClient: {
                _getWindowHash() {
                    return '#action=24';
                }
            },
            mockRPC(route) {
                assert.step(route);
                if (route === '/web/dataset/search_read') {
                    return Promise.reject();
                }
                return this._super.apply(this, arguments);
            }
        });
        assert.containsOnce(webClient, '.o_form_view');
        assert.containsN(webClient, '.o_form_buttons_view button:not([disabled])', 2);

        await testUtils.dom.click(webClient.el.querySelector('.oe_stat_button'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view');

        assert.containsN(webClient, '.o_form_buttons_view button:not([disabled])', 2);

        assert.verifySteps([
            '/web/action/load',
            '/web/dataset/call_kw/partner',
            '/web/dataset/call_kw/partner/read',
            '/web/action/load',
            '/web/dataset/call_kw/partner',
            '/web/dataset/search_read',
            // '/web/dataset/call_kw/partner/read', checked in master 20-03-19
        ]);
        webClient.destroy();
    });

    QUnit.test('execute action without modal', async function (assert) {
        // TODO: I don't like those 2 tooltips
        // Just because there are two bodies
        assert.expect(11);

        Object.assign(this.archs, {
            'partner,666,form': `<form>
                <header><button name="object" string="Call method" type="object" help="need somebody"/></header>
                    <field name="display_name"/>
                </form>`,
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            webClient: {
                _getWindowHash() {
                    return '#action=24';
                }
            },
            mockRPC(route) {
                assert.step(route);
                if (route === '/web/dataset/call_button') {
                    // Some business stuff server side, then return an implicit close action
                    return Promise.resolve(false);
                }
                return this._super.apply(this, arguments);
            }
        });
        assert.verifySteps([
            '/web/action/load',
            '/web/dataset/call_kw/partner',
            '/web/dataset/call_kw/partner/read',
        ]);
        assert.containsN(webClient, '.o_form_buttons_view button:not([disabled])', 2);
        const actionButton = webClient.el.querySelector('button[name=object]');
        const tooltipProm = new Promise((resolve) => {
            $(document.body).one("shown.bs.tooltip", () => {
                $(actionButton).mouseleave();
                resolve();
            });
        });
        $(actionButton).mouseenter();
        await tooltipProm;
        assert.containsN(document.body, '.tooltip', 2);
        await testUtils.dom.click(actionButton);
        await testUtils.owlCompatibilityExtraNextTick();
        assert.verifySteps([
            '/web/dataset/call_button',
            '/web/dataset/call_kw/partner/read',
        ]);
        assert.containsNone(document.body, '.tooltip'); // body different from webClient in tests !
        assert.containsN(webClient, '.o_form_buttons_view button:not([disabled])', 2);
        webClient.destroy();
    });

    QUnit.test('list with default_order and favorite filter with no orderedBy', async function (assert) {
        assert.expect(5);

        this.archs['partner,1,list'] = '<tree default_order="foo desc"><field name="foo"/></tree>';

        this.actions.push({
            id: 12,
            name: 'Partners',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[1, 'list'], [false, 'form']],
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            favoriteFilters: [{
                user_id: [2, "Mitchell Admin"],
                name: 'favorite filter',
                id: 5,
                context: {},
                sort: '[]',
                domain: '[("bar", "=", 1)]'
            }],
        });

        await doAction(12);
        assert.strictEqual($(webClient.el).find('.o_list_view tr.o_data_row .o_data_cell').text(), 'zoupyopplopgnapblip',
            'record should be in descending order as default_order applies');

        await cpHelpers.toggleFavoriteMenu(webClient);
        await cpHelpers.toggleMenuItem(webClient, "favorite filter");
        assert.strictEqual($(webClient.el).find('.o_control_panel .o_facet_values').text().trim(),
            'favorite filter', 'favorite filter should be applied');
        assert.strictEqual($(webClient.el).find('.o_list_view tr.o_data_row .o_data_cell').text(), 'gnapblip',
            'record should still be in descending order after default_order applied');

        // go to formview and come back to listview
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb a:eq(0)'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.strictEqual($(webClient.el).find('.o_list_view tr.o_data_row .o_data_cell').text(), 'gnapblip',
            'order of records should not be changed, while coming back through breadcrumb');

        // remove filter
        await cpHelpers.removeFacet(webClient, 0);
        assert.strictEqual($(webClient.el).find('.o_list_view tr.o_data_row .o_data_cell').text(),
            'zoupyopplopgnapblip', 'order of records should not be changed, after removing current filter');

        webClient.destroy();
    });

    QUnit.test("search menus are still available when switching between actions", async function (assert) {
        assert.expect(3);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        await doAction(1);
        assert.isVisible(webClient.el.querySelector('.o_search_options .o_dropdown.o_filter_menu'),
            "the search options should be available");

        await doAction(3);
        assert.isVisible(webClient.el.querySelector('.o_search_options .o_dropdown.o_filter_menu'),
            "the search options should be available");

        // go back using the breadcrumbs
        await testUtils.dom.click($('.o_control_panel .breadcrumb a:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.isVisible(webClient.el.querySelector('.o_search_options .o_dropdown.o_filter_menu'),
            "the search options should be available");

        webClient.destroy();
    });

    QUnit.test("current act_window action is stored in session_storage", async function (assert) {
        assert.expect(1);

        var expectedAction = _.extend({}, _.findWhere(this.actions, {id: 3}), {
            context: {},
        });
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            services: {
                session_storage: SessionStorageService.extend({
                    setItem: function (key, value) {
                        assert.strictEqual(value, JSON.stringify(expectedAction),
                            "should store the executed action in the sessionStorage");
                    },
                }),
            },
        });

        await doAction(3);

        webClient.destroy();
    });

    QUnit.test("store evaluated context of current action in session_storage", async function (assert) {
        // this test ensures that we don't store stringified instances of
        // CompoundContext in the session_storage, as they would be meaningless
        // once restored
        assert.expect(1);

        var expectedAction = _.extend({}, _.findWhere(this.actions, {id: 4}), {
            context: {
                active_model: 'partner',
                active_id: 1,
                active_ids: [1],
            },
            flags: {
                searchPanelDefaultNoFilter: true,
            },
        });
        var checkSessionStorage = false;
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            services: {
                session_storage: SessionStorageService.extend({
                    setItem: function (key, value) {
                        if (checkSessionStorage) {
                            assert.strictEqual(value, JSON.stringify(expectedAction),
                                "should correctly store the executed action in the sessionStorage");
                        }
                    },
                }),
            },
        });

        // execute an action and open a record in form view
        await doAction(3);
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        // click on 'Execute action' button (it executes an action with a CompoundContext as context)
        checkSessionStorage = true;
        await testUtils.dom.click($(webClient.el).find('.o_form_view button:contains(Execute action)'));
        await testUtils.owlCompatibilityExtraNextTick();

        webClient.destroy();
    });

    QUnit.test("destroy action with lazy loaded controller", async function (assert) {
        assert.expect(6);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            webClient: {
                _getWindowHash() {
                    return `#action=3&id=2&view_type=form`;
                }
            }
        });
        assert.containsNone(webClient, '.o_list_view');
        assert.containsOnce(webClient, '.o_form_view');
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item:last').text(), 'Second record',
            "breadcrumbs should contain the display_name of the opened record");

        await doAction(1, {clear_breadcrumbs: true});

        assert.containsNone(webClient, '.o_form_view');
        assert.containsOnce(webClient, '.o_kanban_view');

        webClient.destroy();
    });

    QUnit.test('execute action from dirty, new record, and come back', async function (assert) {
        assert.expect(19);

        this.data.partner.fields.bar.default = 1;
        this.archs['partner,false,form'] = '<form>' +
                                                '<field name="foo"/>' +
                                                '<field name="bar" readonly="1"/>' +
                                            '</form>';

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'get_formview_action') {
                    return Promise.resolve({
                        res_id: 1,
                        res_model: 'partner',
                        type: 'ir.actions.act_window',
                        views: [[false, 'form']],
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // execute an action and create a new record
        await doAction(3);
        await testUtils.dom.click($(webClient.el).find('.o_list_button_add'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view.o_form_editable');
        assert.containsOnce($(webClient.el), '.o_form_uri:contains(First record)');
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(),
            "PartnersNew");

        // set form view dirty and open m2o record
        await testUtils.fields.editInput($(webClient.el).find('input[name=foo]'), 'val');
        await testUtils.dom.click($(webClient.el).find('.o_form_uri:contains(First record)'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce($('body'), '.modal'); // confirm discard dialog

        // confirm discard changes
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_form_view.o_form_readonly');
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(),
            "PartnersNewFirst record");

        // go back to New using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb-item:nth(1) a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view.o_form_editable');
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb-item').text(),
            "PartnersNew");

        assert.verifySteps([
            '/web/action/load', // action 3
            'load_views', // views of action 3
            '/web/dataset/search_read', // list
            'default_get', // form (create)
            'name_get', // m2o in form
            'get_formview_action', // click on m2o
            'load_views', // form view of dynamic action
            'read', // form
            'default_get', // form (create)
            'name_get', // m2o in form
        ]);

        webClient.destroy();
    });

    QUnit.test('open form view, use the pager, execute action, and come back', async function (assert) {
        assert.expect(8);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        // execute an action and open a record
        await doAction(3);
        assert.containsOnce(webClient, '.o_list_view');
        assert.containsN(webClient, '.o_list_view .o_data_row', 5);
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view');
        assert.strictEqual($(webClient.el).find('.o_field_widget[name=display_name]').text(), 'First record');

        // switch to second record
        await testUtils.dom.click($(webClient.el).find('.o_pager_next'));
        assert.strictEqual($(webClient.el).find('.o_field_widget[name=display_name]').text(), 'Second record');

        // execute an action from the second record
        await testUtils.dom.click($(webClient.el).find('.o_statusbar_buttons button[name=4]'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_kanban_view');

        // go back using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb-item:nth(1) a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view');
        assert.strictEqual($(webClient.el).find('.o_field_widget[name=display_name]').text(), 'Second record');

        webClient.destroy();
    });

    QUnit.test('create a new record in a form view, execute action, and come back', async function (assert) {
        assert.expect(8);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        // execute an action and create a new record
        await doAction(3);
        assert.containsOnce(webClient, '.o_list_view');
        await testUtils.dom.click($(webClient.el).find('.o_list_button_add'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view');
        assert.hasClass($(webClient.el).find('.o_form_view'), 'o_form_editable');
        await testUtils.fields.editInput($(webClient.el).find('.o_field_widget[name=display_name]'), 'another record');
        await testUtils.dom.click($(webClient.el).find('.o_form_button_save'));
        assert.hasClass($(webClient.el).find('.o_form_view'), 'o_form_readonly');

        // execute an action from the second record
        await testUtils.dom.click($(webClient.el).find('.o_statusbar_buttons button[name=4]'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_kanban_view');

        // go back using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb-item:nth(1) a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view');
        assert.hasClass($(webClient.el).find('.o_form_view'), 'o_form_readonly');
        assert.strictEqual($(webClient.el).find('.o_field_widget[name=display_name]').text(), 'another record');

        webClient.destroy();
    });

    QUnit.test('open a record, come back, and create a new record', async function (assert) {
        assert.expect(7);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        // execute an action and open a record
        await doAction(3);
        assert.containsOnce(webClient, '.o_list_view');
        assert.containsN(webClient, '.o_list_view .o_data_row', 5);
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view');
        assert.hasClass($(webClient.el).find('.o_form_view'), 'o_form_readonly');

        // go back using the breadcrumbs
        await testUtils.dom.click($(webClient.el).find('.o_control_panel .breadcrumb-item a'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_list_view');

        // create a new record
        await testUtils.dom.click($(webClient.el).find('.o_list_button_add'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view');
        assert.hasClass($(webClient.el).find('.o_form_view'), 'o_form_editable');

        webClient.destroy();
    });

    QUnit.test('execute a contextual action from a form view', async function (assert) {
        assert.expect(4);

        const contextualAction = this.actions.find(action => action.id === 8);
        contextualAction.context = "{}"; // need a context to evaluate

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: async function (route, args) {
                const res = await this._super(...arguments);
                if (args.method === 'load_views' && args.model === 'partner') {
                    assert.strictEqual(args.kwargs.options.toolbar, true,
                        "should ask for toolbar information");
                    res.form.toolbar = {
                        action: [contextualAction],
                        print: [],
                    };
                }
                return res;
            },
        });

        // execute an action and open a record
        await testUtils.actionManager.doAction(3);
        assert.containsOnce(webClient, '.o_list_view');
        await testUtils.dom.click(webClient.$('.o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view');

        // execute the custom action from the action menu
        await cpHelpers.toggleActionMenu(webClient);
        await cpHelpers.toggleMenuItem(webClient, "Favorite Ponies");
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_list_view');

        webClient.destroy();
    });

    QUnit.module('Actions in target="new"');

    QUnit.test('can execute act_window actions in target="new"', async function (assert) {
        assert.expect(7);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(5);

        assert.containsOnce(document.body, '.o_technical_modal .o_form_view',
            "should have rendered a form view in a modal");
        assert.hasClass($('.o_technical_modal .modal-content'), 'o_act_window',
            "dialog main element should have classname 'o_act_window'");
        assert.hasClass($('.o_technical_modal .o_form_view'), 'o_form_editable',
            "form view should be in edit mode");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            'default_get',
        ]);

        webClient.destroy();
    });

    QUnit.test('chained action on_close', async function (assert) {
        assert.expect(3);

        function on_close() {
            assert.step('Close Action');
        }

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(5, {on_close: on_close});

        // a target=new action shouldn't activate the on_close
        await doAction(5);
        assert.verifySteps([]);

        // An act_window_close should trigger the on_close
        await doAction(10);
        assert.verifySteps(['Close Action']);

        webClient.destroy();
    });

    QUnit.test('footer buttons are moved to the dialog footer', async function (assert) {
        assert.expect(3);

        this.archs['partner,false,form'] = '<form>' +
                '<field name="display_name"/>' +
                '<footer>' +
                    '<button string="Create" type="object" class="infooter"/>' +
                '</footer>' +
            '</form>';

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(5);

        assert.containsNone($('.o_technical_modal .modal-body'), 'button.infooter',
            "the button should not be in the body");
        assert.containsOnce($('.o_technical_modal .modal-footer'), 'button.infooter',
            "the button should be in the footer");
        assert.containsOnce($('.o_technical_modal .modal-footer'), 'button',
            "the modal footer should only contain one button");

        webClient.destroy();
    });

    QUnit.test('footer buttons are updated when having another action in target "new"', async function (assert) {
        assert.expect(9);

        this.archs['partner,false,form'] = '<form>' +
                '<field name="display_name"/>' +
                '<footer>' +
                    '<button string="Create" type="object" class="infooter"/>' +
                '</footer>' +
            '</form>';

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction(5);
        assert.containsNone(webClient, '.o_technical_modal .modal-body button[special="save"]');
        assert.containsNone(webClient, '.o_technical_modal .modal-body button.infooter');
        assert.containsOnce(webClient, '.o_technical_modal .modal-footer button.infooter');
        assert.containsOnce(webClient, '.o_technical_modal .modal-footer button');

        await doAction(25);
        assert.containsNone(webClient, '.o_technical_modal .modal-body button.infooter');
        assert.containsNone(webClient, '.o_technical_modal .modal-footer button.infooter');
        assert.containsNone(webClient, '.o_technical_modal .modal-body button[special="save"]');
        assert.containsOnce(webClient, '.o_technical_modal .modal-footer button[special="save"]');
        assert.containsOnce(webClient, '.o_technical_modal .modal-footer button');

        webClient.destroy();
    });

    QUnit.test('buttons of client action in target="new" and transition to MVC action', async function (assert) {
        assert.expect(4);

        var ClientAction = AbstractAction.extend({
            renderButtons($target) {
                const button = document.createElement('button');
                button.setAttribute('class', 'o_stagger_lee');
                $target[0].appendChild(button);
            },
        });
        core.action_registry.add('test', ClientAction);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction({
            tag: 'test',
            target: 'new',
            type: 'ir.actions.client',
        });
        assert.containsOnce(webClient, '.modal footer button.o_stagger_lee');
        assert.containsNone(webClient, '.modal footer button[special="save"]');
        await doAction(25);
        assert.containsNone(webClient, '.modal footer button.o_stagger_lee');
        assert.containsOnce(webClient, '.modal footer button[special="save"]');

        webClient.destroy();
        delete core.action_registry.map.test;
    });

    QUnit.test('on_attach_callback is called for actions in target="new"', async function (assert) {
        assert.expect(3);

        var ClientAction = AbstractAction.extend({
            on_attach_callback: function () {
                assert.step('on_attach_callback');
            },
            start: function () {
                this.$el.addClass('o_test');
            },
        });
        core.action_registry.add('test', ClientAction);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction({
            tag: 'test',
            target: 'new',
            type: 'ir.actions.client',
        });

        assert.containsOnce(document.body, '.modal .o_test',
            "should have rendered the client action in a dialog");
        assert.verifySteps(['on_attach_callback']);

        webClient.destroy();
        delete core.action_registry.map.test;
    });

    QUnit.module('Actions in target="inline"');

    QUnit.test('form views for actions in target="inline" open in edit mode', async function (assert) {
        assert.expect(5);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(6);

        assert.containsOnce(webClient, '.o_form_view.o_form_editable',
            "should have rendered a form view in edit mode");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            'read',
        ]);

        webClient.destroy();
    });

    QUnit.module('Actions in target="fullscreen"');

    QUnit.test('correctly execute act_window actions in target="fullscreen"', async function (assert) {
        assert.expect(7);

        this.actions[0].target = 'fullscreen';
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        await doAction(1);

        assert.strictEqual($(webClient.el).find('.o_control_panel').length, 1,
            "should have rendered a control panel");
        assert.containsOnce(webClient, '.o_kanban_view',
            "should have rendered a kanban view");
        assert.hasClass(webClient.el, 'o_fullscreen');
        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read',
        ]);

        webClient.destroy();
    });

    QUnit.test('fullscreen on action change: back to a "current" action', async function (assert) {
        assert.expect(7);

        const menus = {
            all_menu_ids: [999, 1],
            children: [{
                id: 999,
                action: 'ir.actions.act_window,6',
                name: 'MAIN APP',
                children: [{
                    id: 1,
                    name: 'P1',
                    children: [],
                }]
            }],
        };

        this.actions[0].target = 'fullscreen';
        this.archs['partner,false,form'] = `
            <form>
                <button name="1" type="action" class="oe_stat_button"/>
            </form>`;

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: menus,
        });

        assert.containsOnce(webClient, 'nav .o_menu_brand');
        assert.strictEqual(webClient.el.querySelector('nav .o_menu_brand').textContent, 'MAIN APP');

        assert.doesNotHaveClass(webClient.el, 'o_fullscreen');

        await testUtils.dom.click($(webClient.el).find('button[name=1]'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.hasClass(webClient.el, 'o_fullscreen');

        await testUtils.dom.click($(webClient.el).find('.breadcrumb li a:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.doesNotHaveClass(webClient.el, 'o_fullscreen');

        assert.containsOnce(webClient, 'nav .o_menu_brand');
        assert.strictEqual(webClient.el.querySelector('nav .o_menu_brand').textContent, 'MAIN APP');

        webClient.destroy();
    });

    QUnit.test('fullscreen on action change: back to another "current" action', async function (assert) {
        assert.expect(8);

        const menus = {
            all_menu_ids: [999, 1],
            children: [{
                id: 999,
                action: 'ir.actions.act_window,6',
                name: 'MAIN APP',
                children: [{
                    id: 1,
                    name: 'P1',
                    children: [],
                }]
            }],
        };

        this.actions[0].target = 'fullscreen';
        this.archs['partner,false,form'] = `
            <form>
                <button name="24" type="action" class="oe_stat_button"/>
            </form>`;

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: menus,
        });

        assert.containsOnce(webClient, 'nav .o_menu_brand');
        assert.strictEqual(webClient.el.querySelector('nav .o_menu_brand').textContent, 'MAIN APP');
        assert.doesNotHaveClass(webClient.el, 'o_fullscreen');

        await testUtils.dom.click(webClient.el.querySelector('button[name="24"]'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.doesNotHaveClass(webClient.el, 'o_fullscreen');

        await testUtils.dom.click(webClient.el.querySelector('button[name="1"]'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.hasClass(webClient.el, 'o_fullscreen');

        await testUtils.dom.click(webClient.el.querySelectorAll('.breadcrumb li a')[1]);
        await testUtils.owlCompatibilityExtraNextTick();
        assert.doesNotHaveClass(webClient.el, 'o_fullscreen');

        assert.containsOnce(webClient, 'nav .o_menu_brand');
        assert.strictEqual(webClient.el.querySelector('nav .o_menu_brand').textContent, 'MAIN APP');

        webClient.destroy();
    });

    QUnit.test('fullscreen on action change: all "fullscreen" actions', async function (assert) {
        assert.expect(3);

        this.actions[5].target = 'fullscreen';
        this.archs['partner,false,form'] = `
            <form>
                <button name="1" type="action" class="oe_stat_button"/>
            </form>`;

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        await doAction(6);
        assert.hasClass(webClient.el, 'o_fullscreen');

        await testUtils.dom.click($(webClient.el).find('button[name=1]'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.hasClass(webClient.el, 'o_fullscreen');

        await testUtils.dom.click($(webClient.el).find('.breadcrumb li a:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.hasClass(webClient.el, 'o_fullscreen');

        webClient.destroy();
    });

    QUnit.module('"ir.actions.act_window_close" actions');

    QUnit.test('close the currently opened dialog', async function (assert) {
        assert.expect(2);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        // execute an action in target="new"
        await doAction(5);
        assert.strictEqual($('.o_technical_modal .o_form_view').length, 1,
            "should have rendered a form view in a modal");

        // execute an 'ir.actions.act_window_close' action
        await doAction({
            type: 'ir.actions.act_window_close',
        });
        assert.strictEqual($('.o_technical_modal').length, 0,
            "should have closed the modal");

        webClient.destroy();
    });

    QUnit.test('execute "on_close" only if there is no dialog to close', async function (assert) {
        assert.expect(3);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        // execute an action in target="new"
        await doAction(5);

        var options = {
            on_close: assert.step.bind(assert, 'on_close'),
        };
        // execute an 'ir.actions.act_window_close' action
        // should not call 'on_close' as there is a dialog to close
        await doAction({type: 'ir.actions.act_window_close'}, options);

        assert.verifySteps([]);

        // execute again an 'ir.actions.act_window_close' action
        // should call 'on_close' as there is no dialog to close
        await doAction({type: 'ir.actions.act_window_close'}, options);

        assert.verifySteps(['on_close']);

        webClient.destroy();
    });

    QUnit.skip('doAction resolved with an action', async function (assert) {
        // We could quite easily do something equivalent, with an success callback
        // given in the do-action event payload. However, I'm not sure it's still
        // useful, so if it is not strictly necessary, I would not re-implement
        // the feature for now
        assert.expect(4);

        this.actions.push({
            id: 21,
            name: 'A Close Action',
            type: 'ir.actions.act_window_close',
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        await doAction(21).then(function (action) {
            assert.ok(action, "doAction should be resolved with an action");
            assert.strictEqual(action.id, 21,
                "should be resolved with correct action id");
            assert.strictEqual(action.name, 'A Close Action',
                "should be resolved with correct action name");
            assert.strictEqual(action.type, 'ir.actions.act_window_close',
                "should be resolved with correct action type");
            webClient.destroy();
        });
    });

    QUnit.test('close action with provided infos', async function (assert) {
        assert.expect(1);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        var options = {
            on_close: function (infos) {
                assert.strictEqual(infos, 'just for testing',
                    "should have the correct close infos");
            }
        };

        await doAction({
            type: 'ir.actions.act_window_close',
            infos: 'just for testing',
        }, options);

        webClient.destroy();
    });

    QUnit.test('on close with effect from server', async function (assert) {
        assert.expect(1);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            session: {
                show_effect: true,
            },
            mockRPC(route, args) {
                if (route === '/web/dataset/call_button') {
                    return Promise.resolve({
                        type: 'ir.actions.act_window_close',
                        effect: {
                            type: 'rainbow_man',
                            message: 'button called',
                        }
                    });
                }
                return this._super.apply(this, arguments);
            },
        });
        await doAction(6);
        await testUtils.dom.click(webClient.el.querySelector('button[name="object"]'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_reward');

        webClient.destroy();
    });

    QUnit.test('on close with effect in xml', async function (assert) {
        assert.expect(2);

        this.archs['partner,false,form'] = `
            <form>
                <header>
                    <button string="Call method"
                        name="object"
                        type="object"
                        effect="{'type': 'rainbow_man', 'message': 'rainBowInXML'}"/>
                </header>
                    <field name="display_name"/>
            </form>`;

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            session: {
                show_effect: true,
            },
            mockRPC(route, args) {
                if (route === '/web/dataset/call_button') {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });
        await doAction(6);
        await testUtils.dom.click(webClient.el.querySelector('button[name="object"]'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_reward');
        assert.strictEqual(
            webClient.el.querySelector('.o_reward .o_reward_msg_content').textContent,
            'rainBowInXML'
        );

        webClient.destroy();
    });

    QUnit.test('history back calls on_close handler of dialog action', async function (assert) {
        assert.expect(2);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        // open a new dialog form
        await doAction(this.actions[4], {
            on_close: function () {
                assert.step('on_close');
            },
        });

        webClient.env.bus.trigger('history-back');
        await testUtils.nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.verifySteps(['on_close'], "should have called the on_close handler");

        webClient.destroy();
    });

    QUnit.test('properly drop client actions after new action is initiated', async function (assert) {
        assert.expect(1);

        var slowWillStartDef = testUtils.makeTestPromise();

        var ClientAction = AbstractAction.extend({
            willStart: function () {
                return slowWillStartDef;
            },
        });

        core.action_registry.add('slowAction', ClientAction);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        doAction('slowAction');
        doAction(4);
        slowWillStartDef.resolve();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_kanban_view',
            'should have loaded a kanban view');

        webClient.destroy();
        delete core.action_registry.map.slowAction;
    });

    QUnit.test('abstract action does not crash on navigation_moves', async function (assert) {
        assert.expect(1);
        var ClientAction = AbstractAction.extend({
        });
        core.action_registry.add('ClientAction', ClientAction);
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction('ClientAction');
        webClient.trigger('navigation_move', {direction: 'down'});
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.ok(true); // no error so it's good
        webClient.destroy();
        delete core.action_registry.ClientAction;
    });

    QUnit.test('fields in abstract action does not crash on navigation_moves', async function (assert) {
        assert.expect(1);
        // create a client action with 2 input field
        var inputWidget;
        var secondInputWidget;
        var ClientAction = AbstractAction.extend(StandaloneFieldManagerMixin, {
            init: function () {
                this._super.apply(this, arguments);
                StandaloneFieldManagerMixin.init.call(this);
            },
            start: function () {
                var _self = this;

                return this.model.makeRecord('partner', [{
                    name: 'display_name',
                    type: 'char',
                }]).then(function (recordID) {
                    var record = _self.model.get(recordID);
                    inputWidget = new BasicFields.InputField(_self, 'display_name', record, {mode: 'edit',});
                    _self._registerWidget(recordID, 'display_name', inputWidget);

                    secondInputWidget = new BasicFields.InputField(_self, 'display_name', record, {mode: 'edit',});
                    secondInputWidget.attrs = {className:"secondField"};
                    _self._registerWidget(recordID, 'display_name', secondInputWidget);

                    inputWidget.appendTo(_self.$el);
                    secondInputWidget.appendTo(_self.$el);
                });
            }
        });
        core.action_registry.add('ClientAction', ClientAction);
        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });
        await doAction('ClientAction');
        inputWidget.$el[0].focus();
        var event = $.Event('keydown', {
            which: $.ui.keyCode.TAB,
            keyCode: $.ui.keyCode.TAB,
        });
        $(inputWidget.$el[0]).trigger(event);

        assert.notOk(event.isDefaultPrevented(),
            "the keyboard event default should not be prevented"); // no crash is good
        webClient.destroy();
        delete core.action_registry.ClientAction;
    });

    QUnit.test('web client is not deadlocked when a view crashes', async function (assert) {
        assert.expect(3);

        var readOnFirstRecordDef = testUtils.makeTestPromise();

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                if (args.method === 'read' && args.args[0][0] === 1) {
                    return readOnFirstRecordDef;
                }
                return this._super.apply(this, arguments);
            }
        });

        await doAction(3);

        // open first record in form view. this will crash and will not
        // display a form view
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        readOnFirstRecordDef.reject(new Error("not working as intended"));
        await testUtils.nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_list_view',
            "there should still be a list view in dom");

        // open another record, the read will not crash
        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:eq(2)'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsNone(webClient, '.o_list_view',
            "there should not be a list view in dom");

        assert.containsOnce(webClient, '.o_form_view',
            "there should be a form view in dom");

        webClient.destroy();
    });

    QUnit.test('data-mobile attribute on action button, in desktop', async function (assert) {
        assert.expect(2);

        utils.patch(ActionManager, 'ActionManagerTestPatch', {
            doAction(action, options) {
                const plop = options ? options.plop : undefined;
                assert.strictEqual(plop, undefined);
                return this._super(...arguments);
            },
        });

        this.archs['partner,75,kanban'] = `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div class="oe_kanban_global_click">
                            <field name="display_name"/>
                            <button
                                name="1"
                                string="Execute action"
                                type="action"
                                data-mobile='{"plop": 28}'/>
                        </div>
                    </t>
                </templates>
            </kanban>`;

        this.actions.push({
            id: 100,
            name: 'action 100',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[75, 'kanban']],
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data
        });

        await doAction(100, {});
        await testUtils.dom.click(webClient.$('button[data-mobile]:first'));
        await testUtils.owlCompatibilityExtraNextTick();

        webClient.destroy();
        utils.unpatch(ActionManager, 'ActionManagerTestPatch');
    });

    QUnit.module('Search View Action');

    QUnit.test('search view should keep focus during do_search', async function (assert) {
        assert.expect(5);

        /* One should be able to type something in the search view, press on enter to
         * make the facet and trigger the search, then do this process
         * over and over again seamlessly.
         * Verifying the input's value is a lot trickier than verifying the search_read
         * because of how native events are handled in tests
         */

        var searchPromise = testUtils.makeTestPromise();

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.step('search_read ' + args.domain);
                    if (_.isEqual(args.domain, [['foo', 'ilike', 'm']])) {
                        return searchPromise.then(this._super.bind(this, route, args));
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        await doAction(3);

        await cpHelpers.editSearch(webClient, "m");
        await cpHelpers.validateSearch(webClient);

        assert.verifySteps(["search_read ", "search_read foo,ilike,m"]);

        // Triggering the do_search above will kill the current searchview Input
        await cpHelpers.editSearch(webClient, "o");

        // We have something in the input of the search view. Making the search_read
        // return at this point will trigger the redraw of the view.
        // However we want to hold on to what we just typed
        searchPromise.resolve();
        await cpHelpers.validateSearch(webClient);

        assert.verifySteps(["search_read |,foo,ilike,m,foo,ilike,o"]);

        webClient.destroy();
    });

    QUnit.test('Call twice clearUncommittedChanges in a row does not display twice the discard warning', async function (assert) {
        assert.expect(4);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        // execute an action and edit existing record
        await doAction(3);

        await testUtils.dom.click($(webClient.el).find('.o_list_view .o_data_row:first'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_view.o_form_readonly');

        await testUtils.dom.click($(webClient.el).find('.o_control_panel .o_form_button_edit'));
        assert.containsOnce(webClient, '.o_form_view.o_form_editable');

        await testUtils.fields.editInput($(webClient.el).find('input[name=foo]'), 'val');
        webClient.actionManager._clearUncommittedChanges();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(document.body, '.modal'); // confirm discard dialog
        // confirm discard changes
        await testUtils.dom.click($('.modal .modal-footer .btn-primary'));
        await testUtils.owlCompatibilityExtraNextTick();

        webClient.actionManager._clearUncommittedChanges();
        await nextTick();
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsNone(document.body, '.modal');

        webClient.destroy();
    });

    QUnit.test('on_close should be called only once', async function (assert) {
        /**
         * TODO: Improve this test
         *
         * When clicking on dialog button it should trigger act_window_close and
         * then execute_action (that will be redirected to an act_window_close)
         *
         * The execute_action comes from BasicController._callButtonAction
         *
         * A real case: event_configurator_widget.js
         */
        assert.expect(2);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            menus: this.menus,
        });

        await doAction(3);
        await testUtils.dom.click(webClient.el.querySelector('.o_list_view .o_data_row'));
        await testUtils.owlCompatibilityExtraNextTick();
        await testUtils.dom.click(webClient.el.querySelector('.o_form_buttons_view .o_form_button_edit'));

        await doAction(25, {
            on_close() {
                assert.step('on_close');
            },
        });

        // Close dialog by clicking on save button
        await testUtils.dom.click(webClient.el.querySelector('.o_dialog .modal-footer button[special=save]'));
        await testUtils.owlCompatibilityExtraNextTick();
        // Directly do act_window_close
        await doAction(10);

        assert.verifySteps(['on_close']);

        webClient.destroy();
    });
});

});
