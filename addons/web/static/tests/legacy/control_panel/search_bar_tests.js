/** @odoo-module alias="web.search_bar_tests" **/

import testUtils from "web.test_utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import { Model } from "web.Model";
import Registry from "web.Registry";
import SearchBar from "web.SearchBar";
import { registry } from "@web/core/registry";
import * as cpHelpers from "@web/../tests/search/helpers";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";

let serverData;
QUnit.module("Search Bar (legacy)", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        bar: { string: "Bar", type: "many2one", relation: "partner" },
                        birthday: { string: "Birthday", type: "date" },
                        birth_datetime: { string: "Birth DateTime", type: "datetime" },
                        foo: { string: "Foo", type: "char" },
                        bool: { string: "Bool", type: "boolean" },
                        status: { string: 'Status', type: 'selection', selection: [['draft', "New"], ['cancel', "Cancelled"]] },
                    },
                    records: [
                        { id: 1, display_name: "First record", foo: "yop", bar: 2, bool: true, birthday: '1983-07-15', birth_datetime: '1983-07-15 01:00:00' },
                        { id: 2, display_name: "Second record", foo: "blip", bar: 1, bool: false, birthday: '1982-06-04', birth_datetime: '1982-06-04 02:00:00' },
                        { id: 3, display_name: "Third record", foo: "gnap", bar: 1, bool: false, birthday: '1985-09-13', birth_datetime: '1985-09-13 03:00:00' },
                        { id: 4, display_name: "Fourth record", foo: "plop", bar: 2, bool: true, birthday: '1983-05-05', birth_datetime: '1983-05-05 04:00:00' },
                        { id: 5, display_name: "Fifth record", foo: "zoup", bar: 2, bool: true, birthday: '1800-01-01', birth_datetime: '1800-01-01 05:00:00' },
                    ],
                }
            },
            views: {
                "partner,false,list": `<tree><field name="foo"/></tree>`,
                "partner,false,search": `
                    <search>
                        <field name="foo"/>
                        <field name="birthday"/>
                        <field name="birth_datetime"/>
                        <field name="bar" context="{'bar': self}"/>
                        <filter string="Date Field Filter" name="positive" date="birthday"/>
                        <filter string="Date Field Groupby" name="coolName" context="{'group_by': 'birthday:day'}"/>
                    </search>
                `,
            },
            actions: {
                1: {
                    id: 1,
                    name: "Partners Action",
                    res_model: "partner",
                    search_view_id: [false, "search"],
                    type: "ir.actions.act_window",
                    views: [[false, "list"]],
                },
            },
        };
    });

        QUnit.test("basic rendering", async function (assert) {
            assert.expect(1);

            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1);

            assert.strictEqual(
                document.activeElement,
                webClient.el.querySelector(".o_searchview input.o_searchview_input"),
                "searchview input should be focused"
            );
        });

        QUnit.test("navigation with facets", async function (assert) {
            assert.expect(4);

            patchWithCleanup(browser, { setTimeout: (fn) => fn() });
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1);

            // add a facet
            await cpHelpers.toggleGroupByMenu(webClient);
            await cpHelpers.toggleMenuItem(webClient, 0);
            await cpHelpers.toggleMenuItemOption(webClient, 0, 0);
            assert.containsOnce(webClient, '.o_searchview .o_searchview_facet',
                "there should be one facet");
            assert.strictEqual(document.activeElement,
                webClient.el.querySelector('.o_searchview input.o_searchview_input'));

            // press left to focus the facet
            await testUtils.dom.triggerEvent(document.activeElement, 'keydown', { key: 'ArrowLeft' });
            assert.strictEqual(document.activeElement, webClient.el.querySelector('.o_searchview .o_searchview_facet'));

            // press right to focus the input
            await testUtils.dom.triggerEvent(document.activeElement, 'keydown', { key: 'ArrowRight' });
            assert.strictEqual(document.activeElement, webClient.el.querySelector('.o_searchview input.o_searchview_input'));
        });

        QUnit.test('search date and datetime fields. Support of timezones', async function (assert) {
            assert.expect(4);

            let searchReadCount = 0;

            const webClient = await createWebClient({
                serverData,
                legacyParams: {
                    getTZOffset() {
                        return 360;
                    },
                },
                mockRPC: (route, args) => {
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
                }
            });
            await doAction(webClient, 1);

            // Date case
            let searchInput = webClient.el.querySelector('.o_searchview_input');
            await testUtils.fields.editInput(searchInput, '07/15/1983');
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });

            assert.strictEqual(webClient.el.querySelector('.o_searchview_facet .o_facet_values').innerText.trim(),
                '07/15/1983',
                'The format of the date in the facet should be in locale');

            // Close Facet
            await testUtils.dom.click($('.o_searchview_facet .o_facet_remove'));

            // DateTime case
            searchInput = webClient.el.querySelector('.o_searchview_input');
            await testUtils.fields.editInput(searchInput, '07/15/1983 00:00:00');
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });

            assert.strictEqual(webClient.el.querySelector('.o_searchview_facet .o_facet_values').innerText.trim(),
                '07/15/1983 00:00:00',
                'The format of the datetime in the facet should be in locale');
        });

        QUnit.test("autocomplete menu clickout interactions", async function (assert) {
            assert.expect(9);

            const data = serverData.models;
            const fields = serverData.models.partner.fields;

            class TestModelExtension extends Model.Extension {
                get(property) {
                    switch (property) {
                        case 'facets':
                            return [];
                        case 'filters':
                            return Object.keys(fields).map((fname, index) => Object.assign({
                                description: fields[fname].string,
                                fieldName: fname,
                                fieldType: fields[fname].type,
                                id: index,
                            }, fields[fname]));
                        default:
                            break;
                    }
                }
            }
            class MockedModel extends Model {}
            MockedModel.registry = new Registry({ Test: TestModelExtension, });
            const searchModel = new MockedModel({ Test: {} });


            const searchBar = await testUtils.createComponent(SearchBar, {
                data,
                env: { searchModel },
                props: { fields },
            });
            const input = searchBar.el.querySelector('.o_searchview_input');

            assert.containsNone(searchBar, '.o_searchview_autocomplete');

            await testUtils.controlPanel.editSearch(searchBar, "Hello there");

            assert.strictEqual(input.value, "Hello there", "input value should be updated");
            assert.containsOnce(searchBar, '.o_searchview_autocomplete');

            await testUtils.dom.triggerEvent(input, 'keydown', { key: 'Escape' });

            assert.strictEqual(input.value, "", "input value should be empty");
            assert.containsNone(searchBar, '.o_searchview_autocomplete');

            await testUtils.controlPanel.editSearch(searchBar, "General Kenobi");

            assert.strictEqual(input.value, "General Kenobi", "input value should be updated");
            assert.containsOnce(searchBar, '.o_searchview_autocomplete');

            await testUtils.dom.click(document.body);

            assert.strictEqual(input.value, "", "input value should be empty");
            assert.containsNone(searchBar, '.o_searchview_autocomplete');

            searchBar.destroy();
        });

        QUnit.test('select an autocomplete field', async function (assert) {
            assert.expect(3);

            let searchReadCount = 0;
            const webClient = await createWebClient({
                serverData,
                mockRPC: (route, args) => {
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
                }
            });
            await doAction(webClient, 1);

            const searchInput = webClient.el.querySelector('.o_searchview_input');
            await testUtils.fields.editInput(searchInput, 'a');
            assert.containsN(webClient, '.o_searchview_autocomplete li', 2,
                "there should be 2 result for 'a' in search bar autocomplete");

            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });
            assert.strictEqual(webClient.el.querySelector('.o_searchview_input_container .o_facet_values').innerText.trim(),
                "a", "There should be a field facet with label 'a'");
        });

        QUnit.test('autocomplete input is trimmed', async function (assert) {
            assert.expect(3);

            let searchReadCount = 0;
            const webClient = await createWebClient({
                serverData,
                mockRPC: (route, args) => {
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
                }
            });
            await doAction(webClient, 1);

            const searchInput = webClient.el.querySelector('.o_searchview_input');
            await testUtils.fields.editInput(searchInput, 'a ');
            assert.containsN(webClient, '.o_searchview_autocomplete li', 2,
                "there should be 2 result for 'a' in search bar autocomplete");

            await testUtils.dom.triggerEvent(searchInput, 'keydown', {key: 'Enter'});
            assert.strictEqual(webClient.el.querySelector('.o_searchview_input_container .o_facet_values').innerText.trim(),
                "a", "There should be a field facet with label 'a'");
        });

        QUnit.test('select an autocomplete field with `context` key', async function (assert) {
            assert.expect(9);

            let searchReadCount = 0;
            const firstLoading = testUtils.makeTestPromise();
            const webClient = await createWebClient({
                serverData,
                mockRPC: (route, args) => {
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
                }
            });
            await doAction(webClient, 1);
            await firstLoading;
            assert.strictEqual(searchReadCount, 1, "there should be 1 search_read");
            const searchInput = webClient.el.querySelector('.o_searchview_input');

            // 'r' key to filter on bar "First Record"
            await testUtils.fields.editInput(searchInput, 'record');
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowRight' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });

            assert.strictEqual(webClient.el.querySelector('.o_searchview_input_container .o_facet_values').innerText.trim(),
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

            assert.strictEqual(webClient.el.querySelector('.o_searchview_input_container .o_facet_values').innerText.trim(),
                "First recordorSecond record",
                "the autocompletion facet should be correct");
            assert.strictEqual(searchReadCount, 3, "there should be 3 search_read");
        });

        QUnit.test('no search text triggers a reload', async function (assert) {
            assert.expect(2);

            // Switch to pivot to ensure that the event comes from the control panel
            // (pivot does not have a handler on "reload" event).
            serverData.actions[1].views = [[false, "pivot"]];
            serverData.views['partner,false,pivot'] = `
                <pivot>
                    <field name="foo" type="row"/>
                </pivot>
            `;

            registry.category("services").add("user", makeFakeUserService());

            let rpcs;
            const webClient = await createWebClient({
                serverData,
                mockRPC: () => { rpcs++; },
            });
            await doAction(webClient, 1);

            const searchInput = webClient.el.querySelector('.o_searchview_input');
            rpcs = 0;
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });

            assert.containsNone(webClient, '.o_searchview_facet_label');
            assert.strictEqual(rpcs, 2, "should have reloaded");
        });

        QUnit.test('selecting (no result) triggers a re-render', async function (assert) {
            assert.expect(3);

            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1);

            const searchInput = webClient.el.querySelector('.o_searchview_input');

            // 'a' key to filter nothing on bar
            await testUtils.fields.editInput(searchInput, 'hello there');
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowRight' });
            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'ArrowDown' });

            assert.strictEqual(webClient.el.querySelector('.o_searchview_autocomplete .o_selection_focus').innerText.trim(), "(no result)",
                "there should be no result for 'a' in bar");

            await testUtils.dom.triggerEvent(searchInput, 'keydown', { key: 'Enter' });

            assert.containsNone(webClient, '.o_searchview_facet_label');
            assert.strictEqual(webClient.el.querySelector('.o_searchview_input').value, "",
                "the search input should be re-rendered");
        });

        QUnit.test('update suggested filters in autocomplete menu with Japanese IME', async function (assert) {
            assert.expect(4);

            // The goal here is to simulate as many events happening during an IME
            // assisted composition session as possible. Some of these events are
            // not handled but are triggered to ensure they do not interfere.
            const TEST = "TEST";
            const テスト = "テスト";
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1);

            const searchInput = webClient.el.querySelector('.o_searchview_input');

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
            assert.containsOnce(webClient.el, '.o_searchview_autocomplete',
                "should display autocomplete dropdown menu on typing something in search view"
            );
            assert.strictEqual(
                webClient.el.querySelector('.o_searchview_autocomplete li').innerText.trim(),
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
                webClient.el.querySelector('.o_searchview_autocomplete li').innerText.trim(),
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
                webClient.el.querySelector('.o_searchview_autocomplete li').innerText.trim(),
                "Search Foo for: TEST",
                `1st filter suggestion should finally be updated with click selection on word "TEST" from IME`
            );

        });

        QUnit.test('open search view autocomplete on paste value using mouse', async function (assert) {
            assert.expect(1);

            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1);

            // Simulate paste text through the mouse.
            const searchInput = webClient.el.querySelector('.o_searchview_input');
            searchInput.value = "ABC";
            await testUtils.dom.triggerEvent(searchInput, 'input',
                { inputType: 'insertFromPaste' });
            await testUtils.nextTick();
            assert.containsOnce(webClient, '.o_searchview_autocomplete',
                "should display autocomplete dropdown menu on paste in search view");

        });

        QUnit.test('select autocompleted many2one', async function (assert) {
            assert.expect(5);

            serverData.views['partner,false,search'] = `
                <search>
                    <field name="foo"/>
                    <field name="birthday"/>
                    <field name="birth_datetime"/>
                    <field name="bar" operator="child_of"/>
                </search>
            `;

            const webClient = await createWebClient({
                serverData,
                mockRPC: (route, { domain }) => {
                    if (route === '/web/dataset/search_read') {
                        assert.step(JSON.stringify(domain));
                    }
                },
            });
            await doAction(webClient, 1);

            await testUtils.controlPanel.editSearch(webClient, "rec");
            await testUtils.dom.click(webClient.el.querySelector('.o_searchview_autocomplete li:last-child'));

            await cpHelpers.removeFacet(webClient, 0);

            await testUtils.controlPanel.editSearch(webClient, "rec");
            await testUtils.dom.click(webClient.el.querySelector('.o_expand'));
            await testUtils.dom.click(webClient.el.querySelector('.o_searchview_autocomplete li.o_menu_item.o_indent'));

            assert.verifySteps([
                '[]',
                '[["bar","child_of","rec"]]', // Incomplete string -> Name search
                '[]',
                '[["bar","child_of",1]]', // Suggestion select -> Specific ID
            ]);

        });

        QUnit.test('"null" as autocomplete value', async function (assert) {
            assert.expect(4);

            const webClient = await createWebClient({
                serverData,
                mockRPC: (route, { domain }) => {
                    if (route === '/web/dataset/search_read') {
                        assert.step(JSON.stringify(domain));
                    }
                },
            });
            await doAction(webClient, 1);

            await testUtils.controlPanel.editSearch(webClient, "null");

            assert.strictEqual(
                webClient.el.querySelector('.o_searchview_autocomplete .o_selection_focus').innerText,
                "Search Foo for: null"
            );

            await testUtils.dom.click(webClient.el.querySelector('.o_searchview_autocomplete li.o_selection_focus a'));

            assert.verifySteps([
                JSON.stringify([]), // initial search
                JSON.stringify([["foo", "ilike", "null"]]),
            ]);

        });

        QUnit.test('autocompletion with a boolean field', async function (assert) {
            assert.expect(11);

            serverData.views['partner,false,search'] = `
                <search><field name="bool"/></search>
            `;

            const webClient = await createWebClient({
                serverData,
                mockRPC: (route, { domain }) => {
                    if (route === '/web/dataset/search_read') {
                        assert.step(JSON.stringify(domain));
                    }
                },
            });
            await doAction(webClient, 1);

            await testUtils.controlPanel.editSearch(webClient, "y");

            assert.containsOnce(webClient, '.o_searchview_autocomplete li');
            assert.strictEqual(webClient.el.querySelector('.o_searchview_autocomplete li').innerText, "Search Bool: Yes");
            assert.doesNotHaveClass(webClient.el.querySelector('.o_searchview_autocomplete li'), 'o_indent');

            // select "Yes"
            await testUtils.dom.click(webClient.el.querySelector('.o_searchview_autocomplete li'));

            await cpHelpers.removeFacet(webClient, 0);

            await testUtils.controlPanel.editSearch(webClient, "No");

            assert.containsOnce(webClient, '.o_searchview_autocomplete li');
            assert.strictEqual(webClient.el.querySelector('.o_searchview_autocomplete li').innerText, "Search Bool: No");
            assert.doesNotHaveClass(webClient.el.querySelector('.o_searchview_autocomplete li'), 'o_indent');

            // select "No"
            await testUtils.dom.click(webClient.el.querySelector('.o_searchview_autocomplete li'));

            assert.verifySteps([
                JSON.stringify([]), // initial search
                JSON.stringify([["bool", "=", true]]),
                JSON.stringify([]),
                JSON.stringify([["bool", "=", false]]),
            ]);
        });

        QUnit.test('autocompletion with a selection field', async function (assert) {
            assert.expect(5);

            serverData.views['partner,false,search'] = `
                <search><field name="status"/></search>
            `;

            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1);

            await testUtils.controlPanel.editSearch(webClient, "n");

            assert.containsN(webClient, '.o_searchview_autocomplete li', 2);
            assert.strictEqual(webClient.el.querySelector('.o_searchview_autocomplete li:first-child').innerText, "Search Status: New");
            assert.strictEqual(webClient.el.querySelector('.o_searchview_autocomplete li:last-child').innerText, "Search Status: Cancelled");
            assert.doesNotHaveClass(webClient.el.querySelector('.o_searchview_autocomplete li:first-child'), 'o_indent');
            assert.doesNotHaveClass(webClient.el.querySelector('.o_searchview_autocomplete li:last-child'), 'o_indent');
        });

        QUnit.test("reference fields are supported in search view", async function (assert) {
            assert.expect(7);

            const partnerModel = serverData.models.partner;

            partnerModel.fields.ref = { type: 'reference', string: "Reference" };
            partnerModel.records.forEach((record, i) => {
                record.ref = `ref${String(i).padStart(3, "0")}`;
            });
            serverData.views["partner,false,search"] = `
                <search>
                    <field name="ref"/>
                </search>
            `;

            const webClient = await createWebClient({
                serverData,
                mockRPC: (route, { domain }) => {
                    if (route === '/web/dataset/search_read') {
                        assert.step(JSON.stringify(domain));
                    }
                },
            });
            await doAction(webClient, 1);

            await testUtils.controlPanel.editSearch(webClient, "ref");
            await cpHelpers.validateSearch(webClient);

            assert.containsN(webClient, ".o_data_row", 5);

            await cpHelpers.removeFacet(webClient, 0);
            await testUtils.controlPanel.editSearch(webClient, "ref002");
            await cpHelpers.validateSearch(webClient);

            assert.containsOnce(webClient, ".o_data_row");

            assert.verifySteps([
                '[]',
                '[["ref","ilike","ref"]]',
                '[]',
                '[["ref","ilike","ref002"]]',
            ]);
        });
});
