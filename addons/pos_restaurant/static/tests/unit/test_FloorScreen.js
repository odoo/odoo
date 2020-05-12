odoo.define('pos_restaurant.tests.FloorScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');
    const testUtils = require('web.test_utils');
    const makePosTestEnv = require('point_of_sale.test_env');
    const { xml } = owl.tags;
    const { useRef } = owl.hooks;

    QUnit.module('FloorScreen components', {});

    QUnit.test('TableWidget', async function (assert) {
        assert.expect(9);

        class Parent extends PosComponent {
            constructor() {
                super();
                useListener('select-table', () => assert.step('select-table'));
            }
            get table() {
                // render table T1
                return Object.values(this.env.pos.tables_by_id).find(
                    (table) => table.name === 'T1'
                );
            }
        }
        Parent.env = makePosTestEnv();
        Parent.template = xml/* html */ `
            <div><TableWidget table="table" /></div>
        `;

        const parent = new Parent();
        await parent.mount(testUtils.prepareTarget());

        const tableEl = parent.el.querySelector('.table');
        assert.ok(tableEl.querySelector('span.label').textContent.includes('T1'));
        assert.ok(tableEl.querySelector('span.table-seats').textContent.includes('4'));
        assert.strictEqual(tableEl.style.width, '100px');
        assert.strictEqual(tableEl.style.height, '100px');
        assert.strictEqual(tableEl.style.background, 'rgb(53, 211, 116)');
        assert.strictEqual(tableEl.style.top, '50px');
        assert.strictEqual(tableEl.style.left, '50px');

        await testUtils.dom.click(tableEl);
        assert.verifySteps(['select-table']);

        parent.unmount();
        parent.destroy();
    });

    QUnit.test('EditableTable', async function (assert) {
        assert.expect(11);

        class Parent extends PosComponent {
            constructor() {
                super();
                useListener('save-table', () => assert.step('save-table'));
                this.tableRef = useRef('table-ref');
            }
            get table() {
                // render table T1
                return Object.values(this.env.pos.tables_by_id).find(
                    (table) => table.name === 'T1'
                );
            }
        }
        Parent.env = makePosTestEnv();
        Parent.template = xml/* html */ `
            <div class="floor-map">
                <EditableTable table="table" t-ref="table-ref" />
            </div>
        `;

        const parent = new Parent();
        await parent.mount(testUtils.prepareTarget());

        const tableEl = parent.el.querySelector('.table.selected');
        assert.ok(tableEl.querySelector('span.label').textContent.includes('T1'));
        assert.ok(tableEl.querySelector('span.table-seats').textContent.includes('4'));
        assert.strictEqual(tableEl.style.width, '100px');
        assert.strictEqual(tableEl.style.height, '100px');
        assert.strictEqual(tableEl.style.background, 'rgb(53, 211, 116)');
        assert.strictEqual(tableEl.style.top, '50px');
        assert.strictEqual(tableEl.style.left, '50px');

        parent.tableRef.comp.trigger('resize-end', {
            size: { width: 100, height: 100 },
            loc: { top: 50, left: 50 },
        });
        assert.verifySteps(['save-table']);
        parent.tableRef.comp.trigger('drag-end', { loc: { top: 50, left: 50 } });
        assert.verifySteps(['save-table']);

        parent.unmount();
        parent.destroy();
    });

    QUnit.test('EditBar', async function (assert) {
        assert.expect(26);

        class Parent extends PosComponent {
            constructor() {
                super();
                useListener('create-table', () => assert.step('create-table'));
                useListener('duplicate-table', () => assert.step('duplicate-table'));
                useListener('rename-table', () => assert.step('rename-table'));
                useListener('change-seats-num', () => assert.step('change-seats-num'));
                useListener('change-shape', () => assert.step('change-shape'));
                useListener('set-table-color', this._onSetTableColor);
                useListener('set-floor-color', this._onSetFloorColor);
                useListener('delete-table', () => assert.step('delete-table'));
            }
            get table() {
                // render table T1
                return Object.values(this.env.pos.tables_by_id).find(
                    (table) => table.name === 'T1'
                );
            }
            _onSetTableColor({ detail: color }) {
                assert.step('set-table-color');
                assert.step(color);
            }
            _onSetFloorColor({ detail: color }) {
                assert.step('set-floor-color');
                assert.step(color);
            }
        }
        Parent.env = makePosTestEnv();

        // Part 1: Test EditBar with selected table

        Parent.template = xml/* html */ `
            <div>
                <EditBar selectedTable="table" />
            </div>
        `;

        let parent = new Parent();
        await parent.mount(testUtils.prepareTarget());

        await testUtils.dom.click(parent.el.querySelector('.edit-button i[aria-label=Add]'));
        assert.verifySteps(['create-table']);
        await testUtils.dom.click(parent.el.querySelector('.edit-button i[aria-label=Duplicate]'));
        assert.verifySteps(['duplicate-table']);
        await testUtils.dom.click(parent.el.querySelector('.edit-button i[aria-label=Rename]'));
        assert.verifySteps(['rename-table']);
        await testUtils.dom.click(parent.el.querySelector('.edit-button i[aria-label=Seats]'));
        assert.verifySteps(['change-seats-num']);
        await testUtils.dom.click(
            parent.el.querySelector('.edit-button i[aria-label="Square Shape"]')
        );
        assert.verifySteps(['change-shape']);

        await testUtils.dom.click(parent.el.querySelector('.edit-button i[aria-label=Tint]'));
        await testUtils.nextTick();

        assert.ok(parent.el.querySelector('.color-picker.fg-picker'));
        await testUtils.dom.click(parent.el.querySelector('.fg-picker .color.tl'));
        assert.verifySteps(['set-table-color', '#EB6D6D']);

        await testUtils.dom.click(parent.el.querySelector('.edit-button.trash'));
        assert.verifySteps(['delete-table']);

        parent.unmount();
        parent.destroy();

        // Part 2: Test EditBar without selected table

        Parent.template = xml/* html */ `
            <div>
                <EditBar />
            </div>
        `;

        parent = new Parent();
        await parent.mount(testUtils.prepareTarget());

        assert.ok(parent.el.querySelector('.edit-button.disabled i[aria-label=Duplicate]'));
        assert.ok(parent.el.querySelector('.edit-button.disabled i[aria-label=Rename]'));
        assert.ok(parent.el.querySelector('.edit-button.disabled i[aria-label=Seats]'));
        assert.ok(parent.el.querySelector('.edit-button.disabled i[aria-label="Square Shape"]'));
        assert.ok(parent.el.querySelector('.edit-button.disabled i[aria-label=Delete]'));

        await testUtils.dom.click(parent.el.querySelector('.edit-button i[aria-label=Tint]'));
        await testUtils.nextTick();

        assert.notOk(parent.el.querySelector('.color-picker.fg-picker'));
        assert.ok(parent.el.querySelector('.color-picker.bg-picker'));

        await testUtils.dom.click(parent.el.querySelector('.bg-picker .color.tl'));
        assert.verifySteps(['set-floor-color', 'rgb(244, 149, 149)']);

        parent.unmount();
        parent.destroy();
    });
});
