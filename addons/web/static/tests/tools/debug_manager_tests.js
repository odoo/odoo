odoo.define('web.debugManagerTests', function (require) {
"use strict";

const DebugManager = require('web.DebugManager');
const testUtils = require('web.test_utils');

const createWebClient = testUtils.createWebClient;
const doAction = testUtils.actionManager.doAction;

QUnit.module('DebugManager', {
    beforeEach: function () {
        this.data = {
            'partner': {
                fields: {},
                records: [
                    {id: 1, display_name: "First partner"},
                    {id: 2, display_name: "Second partner"},
                ],
            },
            'ir.ui.view': {
                fields: {},
                records: [],
                check_access_rights: () => true,
            },
            'ir.rule': {
                fields: {},
                records: [],
                check_access_rights: () => true,
            },
            'ir.model.access': {
                fields: {},
                records: [],
                check_access_rights: () => true,
            },
        };

        this.actions = [{
            id: 10,
            name: 'Partners',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[23, 'list'], [8, 'form']],
        }, {
            id: 12,
            name: 'Create a Partner (Dialog)',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[9, 'form']],
            target: 'new',
        }];

        this.archs = {
            'partner,23,list': '<tree><field name="id"/><field name="display_name"/></tree>',
            'partner,8,form': '<form><sheet><field name="display_name"/></sheet></form>',
            'partner,9,form': '<form><sheet><field name="id"/></sheet></form>',
            'partner,99,search': '<search/>',
        };
    },
}, function () {
    QUnit.test("debug manager on a list view with access rights", async function (assert) {
        assert.expect(7);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            SystrayItems: [DebugManager],
        });

        await doAction(10);

        const debugDropdown = webClient.el.querySelector('.o_debug_manager .o_debug_dropdown');
        assert.containsOnce(debugDropdown, 'a[data-action="edit"][data-model="ir.actions.act_window"][data-id="10"]'); // action
        assert.containsOnce(debugDropdown, 'a[data-action="get_view_fields"]'); // view fields
        assert.containsOnce(debugDropdown, 'a[data-action="manage_filters"]'); // manage filters
        assert.containsOnce(debugDropdown, 'a[data-action="translate"]'); // technical translation
        assert.containsOnce(debugDropdown, 'a[data-action="fvg"]'); // fields view get
        assert.containsOnce(debugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="23"]'); // list view
        assert.containsOnce(debugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="99"]'); // control panel view

        webClient.destroy();
    });

    QUnit.test("debug manager on a form view with access rights", async function (assert) {
        assert.expect(10);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            SystrayItems: [DebugManager],
        });

        await doAction(10);
        await testUtils.dom.click('.o_data_row:first');

        const debugDropdown = webClient.el.querySelector('.o_debug_manager .o_debug_dropdown');
        assert.containsOnce(debugDropdown, 'a[data-action="edit"][data-model="ir.actions.act_window"][data-id="10"]'); // action
        assert.containsOnce(debugDropdown, 'a[data-action="get_view_fields"]'); // view fields
        assert.containsOnce(debugDropdown, 'a[data-action="manage_filters"]'); // manage filters
        assert.containsOnce(debugDropdown, 'a[data-action="translate"]'); // technical translation
        assert.containsOnce(debugDropdown, 'a[data-action="set_defaults"]'); // set defaults
        assert.containsOnce(debugDropdown, 'a[data-action="get_metadata"]'); // view metadata
        assert.containsOnce(debugDropdown, 'a[data-action="get_attachments"]'); // manage attachments
        assert.containsOnce(debugDropdown, 'a[data-action="fvg"]'); // fields view get
        assert.containsOnce(debugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="8"]'); // form view
        assert.containsOnce(debugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="99"]'); // control panel view

        webClient.destroy();
    });

    QUnit.test("debug manager on a form view on a new record", async function (assert) {
        assert.expect(10);

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            SystrayItems: [DebugManager],
        });

        await doAction(10);
        await testUtils.dom.click(webClient.$('.o_list_button_add'));

        const debugDropdown = webClient.el.querySelector('.o_debug_manager .o_debug_dropdown');
        assert.containsOnce(debugDropdown, 'a[data-action="edit"][data-model="ir.actions.act_window"][data-id="10"]'); // action
        assert.containsOnce(debugDropdown, 'a[data-action="get_view_fields"]'); // view fields
        assert.containsOnce(debugDropdown, 'a[data-action="manage_filters"]'); // manage filters
        assert.containsOnce(debugDropdown, 'a[data-action="translate"]'); // technical translation
        assert.containsOnce(debugDropdown, 'a[data-action="set_defaults"]'); // set defaults
        assert.containsNone(debugDropdown, 'a[data-action="get_metadata"]'); // view metadata
        assert.containsNone(debugDropdown, 'a[data-action="get_attachments"]'); // manage attachments
        assert.containsOnce(debugDropdown, 'a[data-action="fvg"]'); // fields view get
        assert.containsOnce(debugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="8"]'); // form view
        assert.containsOnce(debugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="99"]'); // control panel view

        webClient.destroy();
    });

    QUnit.test("debug manager on a list view without access rights", async function (assert) {
        assert.expect(7);

        this.data['ir.ui.view'].check_access_rights = () => false;

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            SystrayItems: [DebugManager],
        });

        await doAction(10);

        const debugDropdown = webClient.el.querySelector('.o_debug_manager .o_debug_dropdown');
        assert.containsOnce(debugDropdown, 'a[data-action="edit"][data-model="ir.actions.act_window"][data-id="10"]'); // action
        assert.containsOnce(debugDropdown, 'a[data-action="get_view_fields"]'); // view fields
        assert.containsOnce(debugDropdown, 'a[data-action="manage_filters"]'); // manage filters
        assert.containsOnce(debugDropdown, 'a[data-action="translate"]'); // technical translation
        assert.containsOnce(debugDropdown, 'a[data-action="fvg"]'); // fields view get
        assert.containsNone(debugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="23"]'); // list view
        assert.containsNone(debugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="99"]'); // control panel view

        webClient.destroy();
    });

    QUnit.test("debug manager on a form view without access rights", async function (assert) {
        assert.expect(10);

        this.data['ir.ui.view'].check_access_rights = () => false;

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            SystrayItems: [DebugManager],
        });

        await doAction(10);
        await testUtils.dom.click('.o_data_row:first');

        const debugDropdown = webClient.el.querySelector('.o_debug_manager .o_debug_dropdown');
        assert.containsOnce(debugDropdown, 'a[data-action="edit"][data-model="ir.actions.act_window"][data-id="10"]'); // action
        assert.containsOnce(debugDropdown, 'a[data-action="get_view_fields"]'); // view fields
        assert.containsOnce(debugDropdown, 'a[data-action="manage_filters"]'); // manage filters
        assert.containsOnce(debugDropdown, 'a[data-action="translate"]'); // technical translation
        assert.containsOnce(debugDropdown, 'a[data-action="set_defaults"]'); // set defaults
        assert.containsOnce(debugDropdown, 'a[data-action="get_metadata"]'); // view metadata
        assert.containsOnce(debugDropdown, 'a[data-action="get_attachments"]'); // manage attachments
        assert.containsOnce(debugDropdown, 'a[data-action="fvg"]'); // fields view get
        assert.containsNone(debugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="8"]'); // form view
        assert.containsNone(debugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="99"]'); // control panel view

        webClient.destroy();
    });

    QUnit.test("form: Manage Attachments option", async function (assert) {
        assert.expect(7);

        this.data['ir.attachment'] = {
            fields: {},
            records: [],
        };
        this.archs = Object.assign(this.archs, {
            'ir.attachment,false,list': '<tree><field name="display_name"/></tree>',
            'ir.attachment,false,form': '<form><field name="display_name"/></form>',
            'ir.attachment,false,search': '<search/>',
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            SystrayItems: [DebugManager],
            mockRPC: function (route, args) {
                if (args.model === 'ir.attachment') {
                    if (args.method === 'load_views') {
                        assert.deepEqual(args.kwargs.views,
                            [[false, 'list'], [false, 'form'], [false, 'search']]);
                    }
                    if (route === '/web/dataset/search_read') {
                        assert.deepEqual(args.domain,
                            [['res_model', '=', 'partner'], ['res_id', '=', 1]]);
                        assert.deepEqual(args.context, {
                            bin_size: true,
                            default_res_model: "partner",
                            default_res_id: 1,
                        });
                    }
                }
                return this._super(...arguments);
            }
        });

        await doAction(10);
        const debugDropdown = webClient.el.querySelector('.o_debug_manager .o_debug_dropdown');
        assert.containsNone(debugDropdown, 'a[data-action="get_attachments"]');

        await testUtils.dom.click('.o_data_row:first');
        assert.containsOnce(debugDropdown, 'a[data-action="get_attachments"]');

        await testUtils.dom.click(webClient.el.querySelector('.o_debug_manager > a')); // open dropdown
        await testUtils.dom.click(debugDropdown.querySelector('a[data-action="get_attachments"]'));
        assert.containsOnce(webClient, '.o_list_view');
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb').text(),
            "PartnersFirst partnerManage Attachments");

        webClient.destroy();
    });

    QUnit.test("form: Set Defaults option", async function (assert) {
        assert.expect(4);

        this.data['ir.default'] = {
            fields: {},
            records: [],
        };

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            SystrayItems: [DebugManager],
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/ir.default/set") {
                    assert.deepEqual(args.args,
                        ["partner", "display_name", "First partner", true, true, false],
                        'model, field, value and booleans for current user/company should have been passed');
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        await doAction(10);
        const debugDropdown = webClient.el.querySelector('.o_debug_manager .o_debug_dropdown');
        assert.containsNone(debugDropdown, 'a[data-action="set_defaults"]');

        await testUtils.dom.click('.o_data_row:first');
        assert.containsOnce(debugDropdown, 'a[data-action="set_defaults"]');

        await testUtils.dom.click(webClient.el.querySelector('.o_debug_manager > a')); // open dropdown
        await testUtils.dom.click(debugDropdown.querySelector('a[data-action="set_defaults"]'));
        assert.containsOnce(document.body, '.modal');

        // set a default and save
        $('.modal').find('select[id=formview_default_fields] option[value=display_name]').prop('selected', true);
        await testUtils.dom.click($('.modal').find('.modal-footer button').eq(1));

        webClient.destroy();
    });

    QUnit.test("dialog: debug manager on a form view", async function (assert) {
        assert.expect(17);

        DebugManager.deploy();

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            SystrayItems: [DebugManager],
        });

        await doAction(10);
        await doAction(12);
        await testUtils.owlCompatibilityExtraNextTick();

        const mainDebugDropdown = webClient.el.querySelector('.o_debug_manager .o_debug_dropdown');
        assert.containsOnce(mainDebugDropdown, 'a[data-action="edit"][data-model="ir.actions.act_window"][data-id="10"]'); // action
        assert.containsOnce(mainDebugDropdown, 'a[data-action="get_view_fields"]'); // view fields
        assert.containsOnce(mainDebugDropdown, 'a[data-action="manage_filters"]'); // manage filters
        assert.containsOnce(mainDebugDropdown, 'a[data-action="translate"]'); // technical translation
        assert.containsOnce(mainDebugDropdown, 'a[data-action="fvg"]'); // fields view get
        assert.containsOnce(mainDebugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="23"]'); // list view
        assert.containsOnce(mainDebugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="99"]'); // control panel view

        assert.containsOnce(webClient, '.o_dialogs .o_dialog');
        assert.containsOnce(webClient, '.o_dialogs .o_dialog .modal-header .o_debug_manager');
        const dialogDebugDropdown = webClient.el.querySelector('.o_dialog .modal-header .o_debug_manager .o_debug_dropdown');
        assert.containsOnce(dialogDebugDropdown, 'a[data-action="edit"][data-model="ir.actions.act_window"][data-id="12"]'); // action
        assert.containsOnce(dialogDebugDropdown, 'a[data-action="get_view_fields"]'); // view fields
        assert.containsOnce(dialogDebugDropdown, 'a[data-action="manage_filters"]'); // manage filters
        assert.containsOnce(dialogDebugDropdown, 'a[data-action="translate"]'); // technical translation
        assert.containsOnce(dialogDebugDropdown, 'a[data-action="set_defaults"]'); // set defaults
        assert.containsOnce(dialogDebugDropdown, 'a[data-action="fvg"]'); // fields view get
        assert.containsOnce(dialogDebugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="9"]'); // form view
        assert.containsNone(dialogDebugDropdown, 'a[data-action="edit"][data-model="ir.ui.view"][data-id="99"]'); // control panel view

        webClient.destroy();
        DebugManager.undeploy();
    });
});
});
