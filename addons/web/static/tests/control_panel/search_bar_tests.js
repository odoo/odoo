odoo.define('web.search_bar_tests', function (require) {
    "use strict";

    const testUtils = require('web.test_utils');

    const cpHelpers = testUtils.controlPanel;
    const { createActionManager } = testUtils;

    QUnit.module('Components', {
        beforeEach: function () {
            this.data = {
                partner: {
                    fields: {
                        bar: { string: "Bar", type: 'many2one', relation: 'partner' },
                        birthday: { string: "Birthday", type: 'date' },
                        birth_datetime: { string: "Birth DateTime", type: 'datetime' },
                        foo: { string: "Foo", type: 'char' },
                    },
                    records: [
                        { id: 1, display_name: "First record", foo: "yop", bar: 2, birthday: '1983-07-15', birth_datetime: '1983-07-15 01:00:00' },
                        { id: 2, display_name: "Second record", foo: "blip", bar: 1, birthday: '1982-06-04', birth_datetime: '1982-06-04 02:00:00' },
                        { id: 3, display_name: "Third record", foo: "gnap", bar: 1, birthday: '1985-09-13', birth_datetime: '1985-09-13 03:00:00' },
                        { id: 4, display_name: "Fourth record", foo: "plop", bar: 2, birthday: '1983-05-05', birth_datetime: '1983-05-05 04:00:00' },
                        { id: 5, display_name: "Fifth record", foo: "zoup", bar: 2, birthday: '1800-01-01', birth_datetime: '1800-01-01 05:00:00' },
                    ],
                },
            };

            this.actions = [{
                id: 1,
                name: "Partners Action",
                res_model: 'partner',
                search_view_id: [false, 'search'],
                type: 'ir.actions.act_window',
                views: [[false, 'list']],
            }];

            this.archs = {
                'partner,false,list': `
                <tree>
                    <field name="foo"/>
                </tree>`,
                'partner,false,search': `
                <search>
                    <field name="foo"/>
                    <field name="birthday"/>
                    <field name="birth_datetime"/>
                    <field name="bar" context="{'bar': self}"/>
                    <filter string="Date Field Filter" name="positive" date="birthday"/>
                    <filter string="Date Field Groupby" name="coolName" context="{'group_by': 'birthday:day'}"/>
                </search>`,
            };
        },
    }, function () {

        QUnit.module('SearchBar');

        QUnit.test('basic rendering', async function (assert) {
            assert.expect(1);

            const actionManager = await createActionManager({
                actions: this.actions,
                archs: this.archs,
                data: this.data,
            });
            await actionManager.doAction(1);

            assert.strictEqual(document.activeElement,
                actionManager.el.querySelector('.o_searchview input.o_searchview_input'),
                "searchview input should be focused");

            actionManager.destroy();
        });

        QUnit.test('navigation with facets', async function (assert) {
            assert.expect(4);

            const actionManager = await createActionManager({
                actions: this.actions,
                archs: this.archs,
                data: this.data,
            });
            await actionManager.doAction(1);

            // add a facet
            await cpHelpers.toggleGroupByMenu(actionManager);
            await cpHelpers.toggleMenuItem(actionManager, 0);
            await cpHelpers.toggleMenuItemOption(actionManager, 0, 0);
            assert.containsOnce(actionManager, '.o_searchview .o_searchview_facet',
                "there should be one facet");
            assert.strictEqual(document.activeElement,
                actionManager.el.querySelector('.o_searchview input.o_searchview_input'));

            // press left to focus the facet
            await testUtils.dom.triggerEvent(document.activeElement, 'keydown', { key: 'ArrowLeft' });
            assert.strictEqual(document.activeElement, actionManager.el.querySelector('.o_searchview .o_searchview_facet'));

            // press right to focus the input
            await testUtils.dom.triggerEvent(document.activeElement, 'keydown', { key: 'ArrowRight' });
            assert.strictEqual(document.activeElement, actionManager.el.querySelector('.o_searchview input.o_searchview_input'));

            actionManager.destroy();
        });

        QUnit.test('search date and datetime fields. Support of timezones', async function (assert) {
            assert.expect(4);

            let searchReadCount = 0;
            const actionManager = await createActionManager({
                actions: this.actions,
                archs: this.archs,
                data: this.data,
                session: {
                    getTZOffset() {
                        return 360;
                    }
                },
                async mockRPC(route, args) {
                    if (route === '/web/dataset/search_read') {
                        switch (searchReadCount) {
                            case 0:
                                // Done on loading
                                break;
                            case 1:
                                assert.deepEqual(args.domain, [["birthday", "=", "1983-07-15"]],
                                    "A date should stay what the user has input, but transmitted in server's format");
                                break;
                            case 2:
                                // Done on closing the first facet
                                break;
                            case 3:
                                assert.deepEqual(args.domain, [["birth_datetime", "=", "1983-07-14 18:00:00"]],
                                    "A datetime should be transformed in UTC and transmitted in server's format");
                                break;
                        }
                        searchReadCount++;
                    }
                    return this._super(...arguments);
                },
            });
            await actionManager.doAction(1);

            // Date case
            let searchInput = actionManager.el.querySelector('.o_searchview_input');
            await testUtils.fields.editInput(searchInput, '07/15/1983');
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });

            assert.strictEqual(actionManager.el.querySelector('.o_searchview_facet .o_facet_values').innerText.trim(),
                '07/15/1983',
                'The format of the date in the facet should be in locale');

            // Close Facet
            await testUtils.dom.click($('.o_searchview_facet .o_facet_remove'));

            // DateTime case
            searchInput = actionManager.el.querySelector('.o_searchview_input');
            await testUtils.fields.editInput(searchInput, '07/15/1983 00:00:00');
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });

            assert.strictEqual(actionManager.el.querySelector('.o_searchview_facet .o_facet_values').innerText.trim(),
                '07/15/1983 00:00:00',
                'The format of the datetime in the facet should be in locale');

            actionManager.destroy();
        });

        QUnit.test('select an autocomplete field', async function (assert) {
            assert.expect(3);

            let searchReadCount = 0;
            const actionManager = await createActionManager({
                actions: this.actions,
                archs: this.archs,
                data: this.data,
                async mockRPC(route, args) {
                    if (route === '/web/dataset/search_read') {
                        switch (searchReadCount) {
                            case 0:
                                // Done on loading
                                break;
                            case 1:
                                assert.deepEqual(args.domain, [["foo", "ilike", "a"]]);
                                break;
                        }
                        searchReadCount++;
                    }
                    return this._super(...arguments);
                },
            });
            await actionManager.doAction(1);

            const searchInput = actionManager.el.querySelector('.o_searchview_input');
            await testUtils.fields.editInput(searchInput, 'a');
            assert.containsN(actionManager, '.o_searchview_autocomplete li', 2,
                "there should be 2 result for 'a' in search bar autocomplete");

            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });
            assert.strictEqual(actionManager.el.querySelector('.o_searchview_input_container .o_facet_values').innerText.trim(),
                "a", "There should be a field facet with label 'a'");

            actionManager.destroy();
        });

        QUnit.test('select an autocomplete field with `context` key', async function (assert) {
            assert.expect(9);

            let searchReadCount = 0;
            const firstLoading = testUtils.makeTestPromise();
            const actionManager = await createActionManager({
                actions: this.actions,
                archs: this.archs,
                data: this.data,
                async mockRPC(route, args) {
                    if (route === '/web/dataset/search_read') {
                        switch (searchReadCount) {
                            case 0:
                                firstLoading.resolve();
                                break;
                            case 1:
                                assert.deepEqual(args.domain, [["bar", "=", 1]]);
                                assert.deepEqual(args.context.bar, [1]);
                                break;
                            case 2:
                                assert.deepEqual(args.domain, ["|", ["bar", "=", 1], ["bar", "=", 2]]);
                                assert.deepEqual(args.context.bar, [1, 2]);
                                break;
                        }
                        searchReadCount++;
                    }
                    return this._super(...arguments);
                },
            });
            await actionManager.doAction(1);
            await firstLoading;
            assert.strictEqual(searchReadCount, 1, "there should be 1 search_read");
            const searchInput = actionManager.el.querySelector('.o_searchview_input');

            // 'r' key to filter on bar "First Record"
            await testUtils.fields.editInput(searchInput, 'record');
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowRight' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });

            assert.strictEqual(actionManager.el.querySelector('.o_searchview_input_container .o_facet_values').innerText.trim(),
                "First record",
                "the autocompletion facet should be correct");
            assert.strictEqual(searchReadCount, 2, "there should be 2 search_read");

            // 'r' key to filter on bar "Second Record"
            await testUtils.fields.editInput(searchInput, 'record');
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowRight' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });

            assert.strictEqual(actionManager.el.querySelector('.o_searchview_input_container .o_facet_values').innerText.trim(),
                "First recordorSecond record",
                "the autocompletion facet should be correct");
            assert.strictEqual(searchReadCount, 3, "there should be 3 search_read");

            actionManager.destroy();
        });

        QUnit.test('no search text triggers a reload', async function (assert) {
            assert.expect(2);

            // Switch to pivot to ensure that the event comes from the control panel
            // (pivot does not have a handler on "reload" event).
            this.actions[0].views = [[false, 'pivot']];
            this.archs['partner,false,pivot'] = `
            <pivot>
                <field name="foo" type="row"/>
            </pivot>`;

            let rpcs;
            const actionManager = await createActionManager({
                actions: this.actions,
                archs: this.archs,
                data: this.data,
                mockRPC: function () {
                    rpcs++;
                    return this._super.apply(this, arguments);
                },
            });
            await actionManager.doAction(1);

            const searchInput = actionManager.el.querySelector('.o_searchview_input');
            rpcs = 0;
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });

            assert.containsNone(actionManager, '.o_searchview_facet_label');
            assert.strictEqual(rpcs, 2, "should have reloaded");

            actionManager.destroy();
        });

        QUnit.test('selecting (no result) triggers a re-render', async function (assert) {
            assert.expect(3);

            const actionManager = await createActionManager({
                actions: this.actions,
                archs: this.archs,
                data: this.data,
            });

            await actionManager.doAction(1);

            const searchInput = actionManager.el.querySelector('.o_searchview_input');

            // 'a' key to filter nothing on bar
            await testUtils.fields.editInput(searchInput, 'hello there');
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowRight' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });

            assert.strictEqual(actionManager.el.querySelector('.o_searchview_autocomplete .o_selection_focus').innerText.trim(), "(no result)",
                "there should be no result for 'a' in bar");

            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });

            assert.containsNone(actionManager, '.o_searchview_facet_label');
            assert.strictEqual(actionManager.el.querySelector('.o_searchview_input').value, "",
                "the search input should be re-rendered");

            actionManager.destroy();
        });

        QUnit.test('update suggested filters in autocomplete menu with Japanese IME', async function (assert) {
            assert.expect(4);

            // The goal here is to simulate as many events happening during an IME
            // assisted composition session as possible. Some of these events are
            // not handled but are triggered to ensure they do not interfere.
            const TEST = "TEST";
            const テスト = "テスト";
            const actionManager = await createActionManager({
                actions: this.actions,
                archs: this.archs,
                data: this.data,
            });
            await actionManager.doAction(1);
            const searchInput = actionManager.el.querySelector('.o_searchview_input');

            // Simulate typing "TEST" on search view.
            for (let i = 0; i < TEST.length; i++) {
                const key = TEST[i].toUpperCase();
                await testUtils.dom.triggerEvent(searchInput, 'keydown',
                    { key, isComposing: true });
                if (i === 0) {
                    // Composition is initiated after the first keydown
                    await testUtils.dom.triggerEvent(searchInput, 'compositionstart');
                }
                await testUtils.dom.triggerEvent(searchInput, 'keypress',
                    { key, isComposing: true });
                searchInput.value = TEST.slice(0, i + 1);
                await testUtils.dom.triggerEvent(searchInput, 'keyup',
                    { key, isComposing: true });
                await testUtils.dom.triggerEvent(searchInput, 'input',
                    { inputType: 'insertCompositionText', isComposing: true });
            }
            assert.containsOnce(actionManager.el, '.o_searchview_autocomplete',
                "should display autocomplete dropdown menu on typing something in search view"
            );
            assert.strictEqual(
                actionManager.el.querySelector('.o_searchview_autocomplete li').innerText.trim(),
                "Search Foo for: TEST",
                `1st filter suggestion should be based on typed word "TEST"`
            );

            // Simulate soft-selection of another suggestion from IME through keyboard navigation.
            await testUtils.dom.triggerEvent(searchInput, 'keydown',
                { key: 'ArrowDown', isComposing: true });
            await testUtils.dom.triggerEvent(searchInput, 'keypress',
                { key: 'ArrowDown', isComposing: true });
            searchInput.value = テスト;
            await testUtils.dom.triggerEvent(searchInput, 'keyup',
                { key: 'ArrowDown', isComposing: true });
            await testUtils.dom.triggerEvent(searchInput, 'input',
                { inputType: 'insertCompositionText', isComposing: true });

            assert.strictEqual(
                actionManager.el.querySelector('.o_searchview_autocomplete li').innerText.trim(),
                "Search Foo for: テスト",
                `1st filter suggestion should be updated with soft-selection typed word "テスト"`
            );

            // Simulate selection on suggestion item "TEST" from IME.
            await testUtils.dom.triggerEvent(searchInput, 'keydown',
                { key: 'Enter', isComposing: true });
            await testUtils.dom.triggerEvent(searchInput, 'keypress',
                { key: 'Enter', isComposing: true });
            searchInput.value = TEST;
            await testUtils.dom.triggerEvent(searchInput, 'keyup',
                { key: 'Enter', isComposing: true });
            await testUtils.dom.triggerEvent(searchInput, 'input',
                { inputType: 'insertCompositionText', isComposing: true });

            // End of the composition
            await testUtils.dom.triggerEvent(searchInput, 'compositionend');

            assert.strictEqual(
                actionManager.el.querySelector('.o_searchview_autocomplete li').innerText.trim(),
                "Search Foo for: TEST",
                `1st filter suggestion should finally be updated with click selection on word "TEST" from IME`
            );

            actionManager.destroy();
        });
    });
});
