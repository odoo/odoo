odoo.define('web.web_client_tests_common', function (require) {
"use strict";

const { createWebClientFromClass } = require('web.test_utils_create');
const testUtils = require('web.test_utils');
const WebClient = require('web.WebClientClass');

const createWebClient = createWebClientFromClass.bind(null, WebClient);

QUnit.module('WebClient Common', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {},
                records: [
                    {id: 1, display_name: "First partner"},
                    {id: 2, display_name: "Second partner"},
                ],
                do_something() {}
            },
            product: {
                fields: {},
                records: [
                    {id: 4, display_name: 'Chair'},
                    {id: 6, display_name: 'Table'},
                ],
            },
            task: {
                fields: {},
                records: [],
            },
        };

        this.actions = [{
            id: 10,
            name: 'Partners',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'list'], [false, 'form']],
        }, {
            id: 11,
            name: 'Create a Partner',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
        }, {
            id: 12,
            name: 'Create a Partner (Dialog)',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
            target: 'new',
        }, {
            id: 20,
            name: 'Products',
            res_model: 'product',
            type: 'ir.actions.act_window',
            views: [[false, 'list']],
        }, {
            id: 30,
            name: 'Tasks',
            res_model: 'task',
            type: 'ir.actions.act_window',
            views: [[false, 'kanban']],
        }];

        this.archs = {
            // list views
            'partner,false,list': '<tree><field name="id"/><field name="display_name"/></tree>',
            'product,false,list': '<tree><field name="id"/><field name="display_name"/></tree>',

            // kanban views
            'task,false,kanban': `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <field name="display_name"/>
                        </t>
                    </templates>
                </kanban>`,

            // form views
            'partner,false,form': `
                <form>
                    <header><button name="do_something" string="Call button" type="object"/></header>
                    <sheet>
                      <field name="display_name"/>
                      <notebook>
                        <page string="red" name="red">
                            <div id="righthand">Nick</div>
                         </page>
                         <page string="hell" name="hell">
                             <div id="brokeluce">Tom</div>
                         </page>
                      </notebook>
                    </sheet>
                </form>`,

            // search views
            'partner,false,search': '<search/>',
            'product,false,search': '<search/>',
            'task,false,search': '<search/>',
        };

        this.menus = {
            all_menu_ids: [1, 2, 3, 4, 5, 6],
            children: [{
                id: 1,
                action: 'ir.actions.act_window,10',
                name: "Partners",
                xmlid: 'la_woman1',
                web_icon_data: 'bloop',
                web_icon: 'bloop,bloop,bloop',
                children: [{
                    id: 2,
                    action: 'ir.actions.act_window,10',
                    name: "All Partners",
                    children: [],
                    web_icon: false,
                    xmlid: 'la_woman11',
                    parent_id: [1, 'Partners'],
                }, {
                    id: 3,
                    action: 'ir.actions.act_window,11',
                    name: "New partner",
                    children: [],
                    web_icon: false,
                    xmlid: 'la_woman12',
                    parent_id: [1, 'Partners']
                }, {
                    id: 6,
                    action: 'ir.actions.act_window,12',
                    name: "New partner (Dialog)",
                    children: [],
                    web_icon: false,
                    xmlid: 'la_woman13',
                    parent_id: [1, 'Partners']
                }],
            }, {
                id: 4,
                action: 'ir.actions.act_window,20',
                name: "Products",
                children: [],
                xmlid: 'la_woman2',
                web_icon_data: 'bloop',
                web_icon: 'bloop,bloop,bloop',
            }, {
                id: 5,
                action: 'ir.actions.act_window,30',
                name: "Tasks",
                children: [],
                xmlid: 'la_woman3',
                web_icon_data: 'bloop',
                web_icon: 'bloop,bloop,bloop',
            }],
        };
    },
}, function () {
    QUnit.test('do not call clearUncommittedChanges() when target=new && dialog is opened', async function (assert) {
        assert.expect(2);

        const webClient = await createWebClient({
            data: this.data,
            actions: this.actions,
            archs: this.archs,
            menus: this.menus,
        });
        await testUtils.actionManager.doAction(10);

        // Open Partner form view and enter some text
        await testUtils.dom.click(webClient.el.querySelector('.o_menu_sections a[data-menu-id="3"]'));
        await testUtils.owlCompatibilityExtraNextTick();
        await testUtils.fields.editInput(webClient.el.querySelector('.o_input[name=display_name]'), "TEST");

        // Open dialog without saving should not ask to discard
        await testUtils.dom.click(webClient.el.querySelector('.o_menu_sections a[data-menu-id="6"]'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_dialog');
        assert.containsOnce(webClient, '.o_dialog .o_act_window .o_view_controller');

        webClient.destroy();
    });

    QUnit.test('do not restore when reloading', async function (assert) {
        assert.expect(5);

        const webClient = await createWebClient({
            data: this.data,
            actions: this.actions,
            archs: this.archs,
            menus: this.menus,
            webClient: {
                _getWindowHash() {return '#action=10';}
            }
        });

        await testUtils.dom.click(webClient.el.querySelector('.o_data_row'));
        await testUtils.owlCompatibilityExtraNextTick();
        assert.containsOnce(webClient, '.o_form_buttons_view .o_form_button_edit');

        await testUtils.dom.click(webClient.el.querySelector('.o_form_buttons_view .o_form_button_edit'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_form_buttons_edit .o_form_button_save');
        assert.containsOnce(webClient, '.o_statusbar_buttons button[name=do_something]');

        await testUtils.dom.click(webClient.el.querySelector('.o_statusbar_buttons button[name=do_something]'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_form_buttons_edit .o_form_button_save');

        await testUtils.dom.click(webClient.el.querySelector('.o_form_buttons_edit .o_form_button_save'));
        await testUtils.owlCompatibilityExtraNextTick();

        assert.containsOnce(webClient, '.o_form_buttons_view .o_form_button_edit');

        webClient.destroy();
    });

    QUnit.test('can set window title', async function (assert) {
        assert.expect(6);

        const webClient = await createWebClient({
            data: this.data,
            actions: this.actions,
            archs: this.archs,
            menus: this.menus,
            webClient: {
                _getWindowHash() {return '#action=10';},
                _setWindowTitle(title) {
                    assert.step(title);
                }
            }
        });
        const randomEl = document.querySelector('.o_web_client div');
        assert.verifySteps([
            'Partners'
        ]);
        randomEl.dispatchEvent(new CustomEvent('set-title-part', {bubbles: true, detail: {title: 'fire', part: 'b'}}));
        assert.verifySteps([
            'Partners - fire'
        ]);
        randomEl.dispatchEvent(new CustomEvent('set-title-part', {bubbles: true, detail: {title: 'on the bayou', part: 'a'}}));
        assert.verifySteps([
            'on the bayou - Partners - fire'
        ]);
        webClient.destroy();
    });

    QUnit.test('can click on anchor link', async function (assert) {
        assert.expect(2);

        this.archs['partner,false,form'] = `
                <form>
                    <sheet>
                        <a href="#anchored_div" id="the_trigger">The Trigger</a>
                        <br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/>
                        <br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/>
                        <br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/>
                        <br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/>
                        <br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/><br/>
                        <div id="anchored_div">
                            <field name="display_name"/>
                        </div>
                    </sheet>
                </form>`;

        let targetRect = null;
        const webClient = await createWebClient({
            data: this.data,
            actions: this.actions,
            archs: this.archs,
            menus: this.menus,
            webClient: {
                _scrollTo(data) {
                    const {top, left} = data;
                    assert.strictEqual(top, targetRect.top);
                    assert.strictEqual(left, targetRect.left);
                    return this._super.apply(this, arguments);
                }
            },
        });
        await testUtils.actionManager.doAction(11, {resID: 1});
        const anchorTarget = document.getElementById('anchored_div');
        targetRect = anchorTarget.getBoundingClientRect();
        await testUtils.dom.click(document.getElementById('the_trigger'));

        webClient.destroy();
    });

    QUnit.test('can click on form notebook in main action', async function (assert) {
        assert.expect(4);
        const webClient = await createWebClient({
            data: this.data,
            actions: this.actions,
            archs: this.archs,
            menus: this.menus,
        });
        await testUtils.actionManager.doAction(11, {resID: 1});
        assert.isVisible(webClient.el.querySelector('#righthand'));
        assert.isNotVisible(webClient.el.querySelector('#brokeluce'));

        await testUtils.dom.click(webClient.el.querySelectorAll('a[data-toggle="tab"]')[1]);
        assert.isNotVisible(webClient.el.querySelector('#righthand'));
        assert.isVisible(webClient.el.querySelector('#brokeluce'));
        webClient.destroy();
    });

    QUnit.test('can click on form notebook in dialog action', async function (assert) {
        assert.expect(4);
        const webClient = await createWebClient({
            data: this.data,
            actions: this.actions,
            archs: this.archs,
            menus: this.menus,
        });
        await testUtils.actionManager.doAction(12, {resID: 1});
        assert.isVisible(webClient.el.querySelector('.modal #righthand'));
        assert.isNotVisible(webClient.el.querySelector('#brokeluce'));

        await testUtils.dom.click(webClient.el.querySelectorAll('.modal a[data-toggle="tab"]')[1]);
        assert.isNotVisible(webClient.el.querySelector('#righthand'));
        assert.isVisible(webClient.el.querySelector('.modal #brokeluce'));
        webClient.destroy();
    });
})
});