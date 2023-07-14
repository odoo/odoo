/** @odoo-module */

import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import * as testUtils from "@web/../tests/helpers/utils";
import weTestUtils from "@web_editor/../tests/test_utils";
import * as dsHelpers from "@web/../tests/core/domain_selector_tests";

let fixture;
let serverData;

QUnit.module('mass_mailing_favourite_filter', {}, function () {
QUnit.module('favorite filter widget', (hooks) => {
    hooks.beforeEach(() => {
        fixture = testUtils.getFixture();
        const models = weTestUtils.wysiwygData({
            'mailing.mailing': {
                fields: {
                    display_name: {
                        string: 'Display name',
                        type: 'char',
                    },
                    subject: {
                        string: 'subject',
                        type: 'char',
                    },
                    mailing_model_id: {
                        string: 'Recipients',
                        type: 'many2one',
                        relation: 'ir.model',
                    },
                    mailing_model_name: {
                        string: 'Recipients Model Name',
                        type: 'char',
                    },
                    mailing_filter_id: {
                        string: 'Filters',
                        type: 'many2one',
                        relation: 'mailing.filter',
                    },
                    mailing_domain: {
                        string: 'Domain',
                        type: 'char',
                    },
                    mailing_filter_domain: {
                        string: 'Domain',
                        type: 'char',
                        related: 'mailing_filter_id.mailing_domain',
                    },
                    mailing_filter_count: {
                        string: 'filter Count',
                        type: 'integer',
                    },
                },
                records: [{
                    id: 1,
                    display_name: 'Belgian Event promotion',
                    subject: 'Early bird discount for Belgian Events! Register Now!',
                    mailing_model_id: 1,
                    mailing_model_name: 'event',
                    mailing_domain: '[["country","=","be"]]',
                    mailing_filter_id: 1,
                    mailing_filter_count: 1,
                    mailing_filter_domain: '[["country","=","be"]]',
                }, {
                    id: 2,
                    display_name: 'New Users Promotion',
                    subject: 'Early bird discount for new users! Register Now!',
                    mailing_model_id: 1,
                    mailing_filter_count: 1,
                    mailing_model_name: 'event',
                    mailing_domain: '[["new_user","=",True]]',
                    mailing_filter_domain: '[["new_user","=",True]]',
                }],
            },
            'ir.model': {
                fields: {
                    model: {string: 'Model', type: 'char'},
                },
                records: [{
                    id: 1, name: 'Event', model: 'event',
                }, {
                    id: 2, name: 'Partner', model: 'partner',
                }],
            },
            'mailing.filter': {
                fields: {
                    name: {
                        string: 'Name',
                        type: 'char',
                    },
                    mailing_domain: {
                        string: 'Mailing Domain',
                        type: 'char',
                    },
                    mailing_model_id: {
                        string: 'Recipients Model',
                        type: 'many2one',
                        relation: 'ir.model'
                    },
                },
                records: [{
                    id: 1,
                    name: 'Belgian Events',
                    mailing_domain: '[["country","=","be"]]',
                    mailing_model_id: 1,
                }],
            },
        });
        serverData = { models };
        setupViewRegistries();
    });

    QUnit.test('create favorite filter', async (assert) => {
        assert.expect(8);

        await makeView({
            type: "form",
            resModel: "mailing.mailing",
            resId: 2,
            serverData,
            arch: `<form>
                    <field name="display_name"/>
                    <field name="subject"/>
                    <field name="mailing_domain"/>
                    <field name="mailing_model_name" invisible="1"/>
                    <field name="mailing_model_id"/>
                    <field name="mailing_filter_count"/>
                    <field name="mailing_filter_domain" invisible="1"/>
                    <field name="mailing_filter_id"
                        widget="mailing_filter"
                        options="{'no_create': '1', 'no_open': '1', 'domain_field': 'mailing_domain', 'model': 'mailing_model_id'}"/>
                </form>`,
            mockRPC: function (_, { args, model, method }) {
                if (method === 'create' && model === 'mailing.filter') {
                    assert.deepEqual(args[0],
                        [{mailing_domain: '[["new_user","=",True]]', mailing_model_id: 1, name: 'event promo - new users'}],
                        "should pass correct data in create");
                }
            },
        });

        fixture.querySelector('.o_field_mailing_filter input').autocomplete = 'widget';
        const $dropdown = fixture.querySelector('.o_field_mailing_filter .dropdown');
        assert.isNotVisible(fixture.querySelector('.o_mass_mailing_remove_filter'),
            "should hide the option to remove filter if no filter is set");
        assert.isVisible(fixture.querySelector('.o_mass_mailing_save_filter_container'),
            "should have option to save filter if no filter is set");
        await testUtils.click(fixture.querySelector('.o_field_mailing_filter input'));
        assert.containsN($dropdown, 'li.ui-menu-item', 2,
            "there should be only one existing filter and a search more btn");
        // create a new filter
        await testUtils.click(fixture, '.o_mass_mailing_add_filter');
        fixture.querySelector('.o_mass_mailing_filter_name').value = 'event promo - new users';
        // Simulate 'Enter' key, which actually 'clicks' the 'o_mass_mailing_btn_save_filter' btn
        await testUtils.triggerEvent(fixture, '.o_mass_mailing_filter_name', 'keydown', { key: 'Enter'});

        // check if filter is set correctly
        assert.strictEqual(
            fixture.querySelector('.o_field_mailing_filter input').value,
            'event promo - new users', "saved filter should be set automatically");

        await testUtils.nextTick();
        assert.isVisible(fixture.querySelector('.o_mass_mailing_remove_filter'),
            "should have option to remove filter if filter is already set");
        assert.isNotVisible(fixture.querySelector('.o_mass_mailing_save_filter_container'),
            "should not have option to save filter if filter is already set");
        // Ensures input is not focussed otherwise clicking on it will just close the dropdown instead of opening it
        fixture.querySelector('.o_field_mailing_filter .o_input_dropdown input').blur();
        await testUtils.click(fixture.querySelector('.o_field_mailing_filter input'));
        assert.containsN($dropdown, 'li.ui-menu-item', 3,
            "there should be two existing filters and a search more btn");
        await testUtils.clickSave(fixture);
    });

    QUnit.test('unlink favorite filter', async (assert) => {
        assert.expect(10);

        await makeView({
            type: "form",
            resModel: "mailing.mailing",
            resId: 1,
            serverData,
            arch: `<form>
                    <field name="display_name"/>
                    <field name="subject"/>
                    <field name="mailing_domain"/>
                    <field name="mailing_model_id"/>
                    <field name="mailing_filter_domain" invisible="1"/>
                    <field name="mailing_filter_count"/>
                    <field name="mailing_filter_id"
                        widget="mailing_filter"
                        options="{'no_create': '1', 'no_open': '1', 'domain_field': 'mailing_domain', 'model': 'mailing_model_id'}"/>
                </form>`,
            mockRPC: function (route, args) {
                if (args.method === 'unlink' && args.model === 'mailing.filter') {
                    assert.deepEqual(args.args[0], [1], "should pass correct filter ID for deletion");
                } else if (args.method === 'web_save' && args.model === 'mailing.mailing') {
                    assert.strictEqual(args.args[1].mailing_filter_id,
                        false, "filter id should be");
                    assert.strictEqual(args.args[1].mailing_domain,
                        '[["country","=","be"]]', "mailing domain should be retained while unlinking filter");
                }
            },
        });

        assert.strictEqual(
            fixture.querySelector('.o_field_mailing_filter input').value,
            'Belgian Events', "there should be filter set");
        assert.isVisible(fixture.querySelector('.o_mass_mailing_remove_filter'),
            "should have option to remove filter if filter is already set");
        assert.isNotVisible(fixture.querySelector('.o_mass_mailing_save_filter_container'),
            "should hide the option to save filter if filter is already set");
        // unlink filter
        await testUtils.click(fixture.querySelector('.o_mass_mailing_remove_filter'));
        assert.strictEqual(
            fixture.querySelector('.o_field_mailing_filter input').value,
            '', "filter should be empty");
        await testUtils.nextTick();
        assert.isNotVisible(fixture.querySelector('.o_mass_mailing_remove_filter'),
            "should hide the option to remove filter if no filter is set");
        assert.isVisible(fixture.querySelector('.o_mass_mailing_save_filter_container'),
            "should not hide the option to save filter if no filter is set");
        // check drop-down after filter deletion
        fixture.querySelector('.o_field_mailing_filter input').autocomplete = 'widget';
        const $dropdown = fixture.querySelector('.o_field_mailing_filter .dropdown');
        await testUtils.click(fixture.querySelector('.o_field_mailing_filter input'));
        assert.containsOnce($dropdown, 'li.ui-menu-item.o_m2o_no_result',
            "there should be no available filters");
        await testUtils.clickSave(fixture);
    });

    QUnit.test('changing filter correctly applies the domain', async (assert) => {
        assert.expect(2);

        serverData.models.partner = {
            fields: {
                name: {string: 'Name', type: 'char', searchable: true},
            },
            records: [
                {id: 1, name: 'Azure Interior'},
                {id: 2, name: 'Deco Addict'},
                {id: 3, name: 'Marc Demo'},
            ]
        };

        serverData.models['mailing.filter'].records = [{
            id: 1,
            name: 'Azure Partner Only',
            mailing_domain: "[['name','=', 'Azure Interior']]",
            mailing_model_id: 2,
        }];

        serverData.models['mailing.mailing'].records.push({
            id: 3,
            display_name: 'Partner Event promotion',
            subject: 'Early bird discount for Partners!',
            mailing_model_id: 2,
            mailing_model_name: 'partner',
            mailing_filter_count: 1,
            mailing_domain: "[['name','!=', 'Azure Interior']]",
        });

        serverData.models['mailing.mailing'].onchanges = {
            mailing_filter_id: obj => {
                obj.mailing_domain = serverData.models['mailing.filter'].records.filter(r => r.id === obj.mailing_filter_id)[0].mailing_domain;
            },
        };

        await makeView({
            type: "form",
            resModel: "mailing.mailing",
            resId: 3,
            serverData,
            arch: `<form>
                    <field name="display_name"/>
                    <field name="subject"/>
                    <field name="mailing_model_name" invisible="1"/>
                    <field name="mailing_model_id"/>
                    <field name="mailing_filter_count" />
                    <field name="mailing_filter_id" widget="mailing_filter" options="{'no_create': '1', 'no_open': '1', 'domain_field': 'mailing_domain', 'model': 'mailing_model_id'}"/>
                    <group>
                        <field name="mailing_domain" widget="domain" options="{'model': 'mailing_model_name'}"/>
                    </group>
                </form>`,
        });

        assert.equal(fixture.querySelector('.o_domain_show_selection_button').textContent.trim(), '2 record(s)',
            "default domain should filter 2 records (all but Azure)");

        await testUtils.click(fixture.querySelector('.o_field_mailing_filter input'));
        fixture.querySelector('.o_field_mailing_filter input').autocomplete = 'widget';
        const $dropdown = fixture.querySelector('.o_field_mailing_filter .dropdown');
        await testUtils.click($dropdown.lastElementChild, 'li:first-of-type');
        assert.equal(fixture.querySelector('.o_domain_show_selection_button').textContent.trim(), '1 record(s)',
            "applied filter should only display single record (only Azure)");
        await testUtils.clickSave(fixture);
    });

    QUnit.test('filter drop-down and filter icons visibility toggles properly based on filters available', async (assert) => {
        assert.expect(11);

        serverData.models.partner = {
            fields: {
                name: {string: 'Name', type: 'char', searchable: true},
            },
            records: [
                {id: 1, name: 'Azure Interior'},
            ]
        };
        serverData.models.event = {
            fields: {
                name: {string: 'Name', type: 'char', searchable: true},
                country: {string: 'Country', type: 'char', searchable: true},
            },
            records: [
                {id: 1, name: 'BE Event', country: 'be'},
            ]
        };

        serverData.models['mailing.filter'].records = [{
            id: 2,
            name: 'Azure partner',
            mailing_domain: '[["name","=","Azure Interior"]]',
            mailing_model_id: 2,
        }, {
            id: 3,
            name: 'Ready Mat partner',
            mailing_domain: '[["name","=","Ready Mat"]]',
            mailing_model_id: 2,
        }];

        serverData.models['mailing.mailing'].records = [{
            id: 1,
            display_name: 'Belgian Event promotion',
            subject: 'Early bird discount for Belgian Events! Register Now!',
            mailing_model_id: 1,
            mailing_model_name: 'event',
            mailing_domain: '[["country","=","be"]]',
            mailing_filter_id: false,
            mailing_filter_count: 0,
        }];

        serverData.models['mailing.mailing'].onchanges = {
            mailing_model_id: obj => {
                obj.mailing_filter_count = serverData.models['mailing.filter'].records.filter(r => r.mailing_model_id === obj.mailing_model_id).length;
            },
            mailing_filter_id: obj => {
                const filterDomain = serverData.models['mailing.filter'].records.filter(r => r.id === obj.mailing_filter_id)[0].mailing_domain;
                obj.mailing_domain = filterDomain, obj.mailing_filter_domain = filterDomain;
            },
        };

        await makeView({
            type: "form",
            resModel: "mailing.mailing",
            resId: 1,
            serverData,
            arch: `<form>
                    <field name="display_name"/>
                    <field name="subject"/>
                    <field name="mailing_model_name" invisible="1"/>
                    <field name="mailing_model_id"/>
                    <field name="mailing_filter_count" />
                    <field name="mailing_filter_id" widget="mailing_filter"
                        options="{'no_create': '1', 'no_open': '1', 'domain_field': 'mailing_domain', 'model': 'mailing_model_id'}"/>
                    <field name="mailing_filter_domain" invisible="1"/>
                    <group>
                        <field name="mailing_domain" widget="domain" options="{'model': 'mailing_model_name'}"/>
                    </group>
                </form>`,
        });

        assert.isNotVisible(fixture.querySelector('.o_field_mailing_filter .o_input_dropdown'),
            "should hide the drop-down to select a filter because there is no filter available for 'Event'");
        assert.isVisible(fixture.querySelector('.o_mass_mailing_no_filter'),
            "should show custom message because there is no filter available for 'Event'");
        assert.isVisible(fixture.querySelector('.o_mass_mailing_save_filter_container'),
            "should show icon to save the filter because domain is set in the mailing");

        // If domain is not set on mailing and no filter available, both drop-down and icon container are hidden
        await dsHelpers.clickOnButtonDeleteNode(fixture);
        assert.isNotVisible(fixture.querySelector('.o_field_mailing_filter .o_input_dropdown'),
            "should not display drop-down because there is still no filter available to select from");
        assert.isNotVisible(fixture.querySelector('.o_mass_mailing_filter_container'),
            "should not show filter container because there is no filter available and no domain set in mailing");

        // If domain is not set on mailing but filters available, display drop-down but hide the icon container
        await testUtils.clickDropdown(fixture, 'mailing_model_id');
        await testUtils.clickOpenedDropdownItem(fixture, 'mailing_model_id', 'Partner');
        assert.isVisible(fixture.querySelector('.o_field_mailing_filter .o_input_dropdown'),
            "should show the drop-down to select a filter because there are filters available for 'Partner'");
        assert.isNotVisible(fixture.querySelector('.o_mass_mailing_filter_container'),
            "should not show filter container because there is no filter selected and no domain set in mailing");

        // Save / Remove icons visibility
        await testUtils.click(fixture.querySelector('.o_field_mailing_filter input'));
        await testUtils.clickOpenedDropdownItem(fixture, 'mailing_filter_id', 'Azure partner');
        await testUtils.nextTick();
        assert.isVisible(fixture.querySelector('.o_mass_mailing_remove_filter'),
            "should have option to remove filter if filter is selected");
        assert.isNotVisible(fixture.querySelector('.o_mass_mailing_save_filter_container'),
            "should not have option to save filter if filter is selected");

        await dsHelpers.clickOnButtonAddNewRule(fixture);
        await testUtils.nextTick();
        assert.isVisible(fixture.querySelector('.o_mass_mailing_save_filter_container'),
            "should have option to save filter because mailing domain is changed");
        assert.isNotVisible(fixture.querySelector('.o_mass_mailing_remove_filter'),
            "should not have option to remove filter because mailing domain is changed");
    });

    QUnit.test('filter widget works in edit and readonly', async (assert) => {
        assert.expect(4);

        serverData.models.partner = {
            fields: {
                name: { string: 'Name', type: 'char', searchable: true },
            },
        };

        serverData.models['mailing.filter'].records = [{
            id: 1,
            name: 'Azure Partner Only',
            mailing_domain: "[['name','=', 'Azure Interior']]",
            mailing_model_id: 2,
        }];

        serverData.models['mailing.mailing'].records.push({
            id: 3,
            display_name: 'Partner Event promotion',
            subject: 'Early bird discount for Partners!',
            mailing_model_id: 2,
            mailing_model_name: 'partner',
            mailing_filter_count: 1,
            mailing_filter_domain: "[['name','=', 'Azure Interior']]",
            mailing_filter_id: 1,
            mailing_domain: "[['name','=', 'Azure Interior']]",
            state: 'draft',
        });

        serverData.models['mailing.mailing'].fields.state = {
            string: 'Stage',
            type: 'selection',
            selection: [['draft', 'Draft'], ['running', 'Running']]
        };

        serverData.models['mailing.mailing'].onchanges = {
            mailing_filter_id: obj => {
                obj.mailing_domain = serverData.models['mailing.filter'].records.filter(r => r.id === obj.mailing_filter_id)[0].mailing_domain;
            },
        };

        await makeView({
            type: "form",
            resModel: "mailing.mailing",
            resId: 3,
            serverData,
            arch: `<form>
                    <field name="display_name"/>
                    <field name="subject"/>
                    <field name="mailing_model_name" invisible="1"/>
                    <field name="mailing_model_id" readonly="state != 'draft'"/>
                    <field name="mailing_filter_count" />
                    <field name="mailing_filter_id" widget="mailing_filter" options="{'no_create': '1', 'no_open': '1', 'domain_field': 'mailing_domain', 'model': 'mailing_model_id'}"/>
                    <field name="state" widget="statusbar" options="{'clickable' : '1'}"/>
                    <group>
                        <field name="mailing_domain" widget="domain" options="{'model': 'mailing_model_name'}"/>
                    </group>
                </form>`,
        });

        await testUtils.nextTick();
        const selectField = fixture.querySelector("button[data-value='running']");
        assert.containsOnce(fixture, "div[name='mailing_model_id']:not(.o_readonly_modifier)");
        assert.ok(fixture.querySelector(".o_mass_mailing_save_filter_container:not(.d-none)"));
        // set to 'running'
        selectField.dispatchEvent(new Event('click'));
        selectField.dispatchEvent(new Event('change'));
        await testUtils.nextTick();
        assert.containsOnce(fixture, "div[name='mailing_model_id'].o_readonly_modifier");
        assert.ok(fixture.querySelector(".o_mass_mailing_save_filter_container:not(.d-none)"));
    });
});
});
