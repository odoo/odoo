odoo.define('mail.debugManagerTests', function (require) {
"use strict";

const DebugManager = require('web.DebugManager');
const testUtils = require('web.test_utils');

const createWebClient = testUtils.createWebClient;
const doAction = testUtils.actionManager.doAction;

QUnit.module('Mail DebugManager', {
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
        }];

        this.archs = {
            'partner,23,list': '<tree><field name="id"/><field name="display_name"/></tree>',
            'partner,8,form': '<form><sheet><field name="display_name"/></sheet></form>',
            'partner,99,search': '<search/>',
        };
    },
}, function () {

    QUnit.test("Manage Messages", async function (assert) {
        assert.expect(7);

        this.data['mail.message'] = {
            fields: {},
            records: [],
        };
        this.archs = Object.assign(this.archs, {
            'mail.message,false,list': '<tree><field name="display_name"/></tree>',
            'mail.message,false,form': '<form><field name="display_name"/></form>',
            'mail.message,false,search': '<search/>',
        });

        const webClient = await createWebClient({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            SystrayItems: [DebugManager],
            mockRPC: function (route, args) {
                if (args.model === 'mail.message') {
                    if (args.method === 'load_views') {
                        assert.deepEqual(args.kwargs.views,
                            [[false, 'list'], [false, 'form'], [false, 'search']]);
                    }
                    if (route === '/web/dataset/search_read') {
                        assert.deepEqual(args.domain,
                            [['res_id', '=', 1], ['model', '=', 'partner']]);
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
        assert.containsNone(debugDropdown, 'a[data-action="getMailMessages"]');

        await testUtils.dom.click('.o_data_row:first');
        assert.containsOnce(debugDropdown, 'a[data-action="getMailMessages"]');

        await testUtils.dom.click(webClient.el.querySelector('.o_debug_manager > a')); // open dropdown
        await testUtils.dom.click(debugDropdown.querySelector('a[data-action="getMailMessages"]'));
        assert.containsOnce(webClient, '.o_list_view');
        assert.strictEqual($(webClient.el).find('.o_control_panel .breadcrumb').text(),
            "PartnersFirst partnerManage Messages");

        webClient.destroy();
    });
});
});
