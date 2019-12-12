odoo.define('web.menu_tests', function (require) {
    "use strict";

    const testUtils = require('web.test_utils');
    const Menu = require('web.Menu');
    const SystrayMenu = require('web.SystrayMenu');
    const Widget = require('web.Widget');

    const { createWebClient } = testUtils;

    QUnit.module('chrome', {
        beforeEach: function () {
            this.data = {
            partner: {
                fields: {},
                records: [
                    {id: 1, display_name: "First partner"},
                    {id: 2, display_name: "Second partner"},
                ],
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
                    <sheet><field name="display_name"/></sheet>
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
                action: false,
                name: "Partners",
                children: [{
                    id: 2,
                    action: 'ir.actions.act_window,10',
                    name: "All Partners",
                    children: [],
                }, {
                    id: 3,
                    action: 'ir.actions.act_window,11',
                    name: "New partner",
                    children: [],
                }, {
                    id: 6,
                    action: 'ir.actions.act_window,12',
                    name: "New partner (Dialog)",
                    children: [],
                }],
            }, {
                id: 4,
                action: 'ir.actions.act_window,20',
                name: "Products",
                children: []
            }, {
                id: 5,
                action: 'ir.actions.act_window,30',
                name: "Tasks",
                children: [],
            }],
        };
        },
    }, function () {
        QUnit.module('Menu');

        QUnit.test('Systray items: on_attach_callback is called', async function (assert) {
            assert.expect(3);

            // Add some widgets to the systray
            const Widget1 = Widget.extend({
                on_attach_callback: () => assert.step('on_attach_callback widget1')
            });
            const Widget2 = Widget.extend({
                on_attach_callback: () => assert.step('on_attach_callback widget2')
            });

            const webClient = await createWebClient({
                data: this.data,
                actions: this.actions,
                archs: this.archs,
                menus: this.menus,
                SystrayItems: [Widget1, Widget2],
            });

            assert.verifySteps([
                'on_attach_callback widget2',
                'on_attach_callback widget1',
            ]);

            webClient.destroy();
        });

        QUnit.test('Menus keep dropdown when mouseover', async function (assert) {
            assert.expect(11);

            const menus = {
                all_menu_ids: [999, 1, 2, 11, 21],
                children: [{
                    id: 999,
                    action: 'ir.actions.act_window,10',
                    name: 'MAIN APP',
                    children: [{
                        id: 1,
                        name: 'P1',
                        children: [{
                            id: 11,
                            name: 'C11',
                            children: [],
                        }],
                    }, {
                        id: 2,
                        name: 'P2',
                        children: [{
                            id: 21,
                            name: 'C21',
                            children: [],
                        }],
                    }]
                }],
            };

            const webClient = await createWebClient({
                data: this.data,
                actions: this.actions,
                archs: this.archs,
                menus: menus,
                debug: true, // Needed because we are going to use the real DOM, because of mouseover
            });

            const menuItems = webClient.el.querySelectorAll('nav ul.o_menu_sections li');
            assert.strictEqual(menuItems.length, 2);

            assert.containsNone(webClient, '.dropdown-menu.show');
            await testUtils.dom.click(menuItems[0].querySelector('a'));
            assert.containsOnce(webClient, '.dropdown-menu.show');
            assert.strictEqual(webClient.el.querySelector('.dropdown-menu.show').textContent, 'C11');

            // mouseover is tricky
            // https://www.w3.org/TR/DOM-Level-3-Events/#trusted-events
            let rect = menuItems[1].getBoundingClientRect();
            await testUtils.dom.triggerPositionalMouseEvent(rect.x, rect.y + 1, 'mouseover');
            assert.containsOnce(webClient, '.dropdown-menu.show');
            assert.strictEqual(webClient.el.querySelector('.dropdown-menu.show').textContent, 'C21');

            rect = menuItems[0].getBoundingClientRect();
            await testUtils.dom.triggerPositionalMouseEvent(rect.x, rect.y + 1, 'mouseover');
            assert.containsOnce(webClient, '.dropdown-menu.show');
            assert.strictEqual(webClient.el.querySelector('.dropdown-menu.show').textContent, 'C11');

            rect = menuItems[0].getBoundingClientRect();
            await testUtils.dom.triggerPositionalMouseEvent(rect.x, rect.y + 1, 'mouseover');
            assert.containsOnce(webClient, '.dropdown-menu.show');
            assert.strictEqual(webClient.el.querySelector('.dropdown-menu.show').textContent, 'C11');

            await testUtils.dom.click(webClient.el.querySelector('nav'));
            assert.containsNone(webClient, '.dropdown-menu.show');

            webClient.destroy();
        });

        QUnit.test('extra menus when too long', async function (assert) {
            assert.expect(2);
            const allMenusIds = [999];
            const mainAppChildren = [];
            for (let child_id=1; child_id < 99; child_id++) {
                allMenusIds.push(child_id);
                mainAppChildren.push({
                    id: child_id,
                    name: `Child ${child_id}`,
                    children: [],
                });
            }

            const menus = {
                all_menu_ids: allMenusIds,
                children: [{
                    id: 998,
                    action: 'ir.actions.act_window,10',
                    name: 'APP ZERO',
                    children: [],
                }, {
                    id: 999,
                    action: 'ir.actions.act_window,20',
                    name: 'MAIN APP',
                    children: mainAppChildren,
                }]
            };

            const webClient = await createWebClient({
                data: this.data,
                actions: this.actions,
                archs: this.archs,
                menus: menus,
            });
            assert.containsNone(webClient, '.o_extra_menu_items');
            await testUtils.dom.click(webClient.el.querySelector('.o_menu_apps [data-toggle="dropdown"]'));
            await testUtils.dom.click(webClient.el.querySelector('.o_menu_apps [data-menu-id="999"]'));
            // FIXME
            for (let i=0; i<16; i++) {
                await testUtils.nextTick();
            }
            assert.containsOnce(webClient, '.o_extra_menu_items');
            webClient.destroy();
        });
    });
});
