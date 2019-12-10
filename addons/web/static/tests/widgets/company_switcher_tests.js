odoo.define('web.SwitchCompanyMenu_tests', function (require) {
"use strict";

var SwitchCompanyMenu = require('web.SwitchCompanyMenu');
var testUtils = require('web.test_utils');


async function createSwitchCompanyMenu(params) {
    params = params || {};
    var target = params.debug ? document.body :  $('#qunit-fixture');
    var menu = new SwitchCompanyMenu();
    testUtils.mock.addMockEnvironment(menu, params);
    await menu.appendTo(target)
    return menu
}


async function initMockCompanyMenu(assert, params) {
    var menu = await createSwitchCompanyMenu({
        session: {
            ...params.session,
            setCompanies: function (mainCompanyId, companyIds) {
                assert.equal(mainCompanyId, params.assertMainCompany[0], params.assertMainCompany[1]);
                assert.equal(_.intersection(companyIds, params.asserCompanies[0]).length, params.asserCompanies[0].length, params.asserCompanies[1]);
            },
        }
    })
    await testUtils.dom.click(menu.$('.dropdown-toggle'));  // open company switcher dropdown
    return menu
}

async function testSwitchCompany(assert, params) {
    assert.expect(2);
    var menu = await initMockCompanyMenu(assert, params);
    await testUtils.dom.click(menu.$(`div[data-company-id=${params.company}] div.log_into`));
    menu.destroy();
}

async function testToggleCompany(assert, params) {
    assert.expect(2);
    var menu = await initMockCompanyMenu(assert, params);
    await testUtils.dom.click(menu.$(`div[data-company-id=${params.company}] div.toggle_company`));
    menu.destroy();
}

QUnit.module('widgets', {
    beforeEach: async function () {
        this.session_mock_multi = {
            user_companies: {
                current_company: [1, "Company 1"],
                allowed_companies: [[1, "Company 1"], [2, "Company 2"], [3, "Company 3"]],
            },
            user_context: { allowed_company_ids: [1, 3] },
        },
        this.session_mock_single = {
            user_companies: {
                current_company: [1, "Company 1"],
                allowed_companies: [[1, "Company 1"], [2, "Company 2"], [3, "Company 3"]],
            },
            user_context: { allowed_company_ids: [1] },
        }
    },

}, function () {

    QUnit.module('SwitchCompanyMenu', {}, function () {

        QUnit.test("Company switcher basic rendering", async function (assert) {
            assert.expect(6);
            var menu = await createSwitchCompanyMenu({ session: this.session_mock_multi });
            assert.equal(menu.$('.company_label:contains(Company 1)').length, 1, "it should display Company 1")
            assert.equal(menu.$('.company_label:contains(Company 2)').length, 1, "it should display Company 2")
            assert.equal(menu.$('.company_label:contains(Company 3)').length, 1, "it should display Company 3")

            assert.equal(menu.$('div[data-company-id=1] .fa-check-square').length, 1, "Company 1 should be checked")
            assert.equal(menu.$('div[data-company-id=2] .fa-square-o').length, 1, "Company 2 should not be checked")
            assert.equal(menu.$('div[data-company-id=3] .fa-check-square').length, 1, "Company 3 should be checked")
            menu.destroy();
        });
    });

    QUnit.module('SwitchCompanyMenu', {}, function () {

        QUnit.test("Toggle new company in multiple company mode", async function (assert) {
            /**
             *          [x] **Company 1**          [x] **Company 1**
             *  toggle->[ ] Company 2     ====>    [x] Company 2
             *          [x] Company 3              [x] Company 3
             */
            await testToggleCompany(assert, {
                company: 2,
                session: this.session_mock_multi,
                assertMainCompany: [1, "Main company should not have changed"],
                asserCompanies: [[1, 2, 3], "All companies should be activated"],
            });
        });

        QUnit.test("Toggle active company in mutliple company mode", async function (assert) {
            /**
             *          [x] **Company 1**          [x] **Company 1**
             *          [ ] Company 2     ====>    [ ] Company 2
             *  toggle->[x] Company 3              [ ] Company 3
             */
            await testToggleCompany(assert, {
                company: 3,
                session: this.session_mock_multi,
                assertMainCompany: [1, "Main company should not have changed"],
                asserCompanies: [[1], "Companies 3 should be unactivated"],
            });
        });

        QUnit.test("Switch main company in mutliple company mode", async function (assert) {
            /**
             *          [x] **Company 1**          [x] Company 1
             *          [ ] Company 2     ====>    [ ] Company 2
             *  switch->[x] Company 3              [x] **Company 3**
             */
            await testSwitchCompany(assert, {
                company: 3,
                session: this.session_mock_multi,
                assertMainCompany: [3, "Main company should switch to Company 3"],
                asserCompanies: [[1, 3], "Companies 1 and 3 should still be active"],
            });
        });

        QUnit.test("Switch new company in mutliple company mode", async function (assert) {
            /**
             *          [x] **Company 1**          [x] Company 1
             *  switch->[ ] Company 2     ====>    [x] **Company 2**
             *          [x] Company 3              [x] Company 3
             */
            await testSwitchCompany(assert, {
                company: 2,
                session: this.session_mock_multi,
                assertMainCompany: [2, "Company 2 should become the main company"],
                asserCompanies: [[1, 2, 3], "Companies 1 and 3 should still be active"],
            });
        });

        QUnit.test("Switch main company in single company mode", async function (assert) {
            /**
             *          [x] **Company 1**          [ ] Company 1
             *          [ ] Company 2     ====>    [ ] Company 2
             *  switch->[ ] Company 3              [x] **Company 3**
             */
            await testSwitchCompany(assert, {
                company: 3,
                session: this.session_mock_single,
                assertMainCompany: [3, "Main company should switch to Company 3"],
                asserCompanies: [[3], "Companies 1 should no longer be active"],
            });
        });

        QUnit.test("Toggle new company in single company mode", async function (assert) {
            /**
             *          [x] **Company 1**          [ ] **Company 1**
             *          [ ] Company 2     ====>    [ ] Company 2
             *  toggle->[ ] Company 3              [x] Company 3
             */
            await testToggleCompany(assert, {
                company: 3,
                session: this.session_mock_single,
                assertMainCompany: [1, "Company 1 should still be the main company"],
                asserCompanies: [[1, 3], "Company 3 should be activated"],
            });
        });
    });
});
});
