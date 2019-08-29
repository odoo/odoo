odoo.define("point_of_sale.PointOfSaleTests", function (require) {
"use strict";

const { createPointOfSale, isPointOfSaleLoaded } = require("point_of_sale.test_utils");

QUnit.module("Point of Sale");

QUnit.module("pos.ui", {
    beforeEach() {
        this.data = {
            "res.users": {
                fields: {
                    name: { string: "Name", type: "char" },
                    company_id: { string: "Company", type: "many2one", relation: "res.company" },
                    groups_id: { string: "Groups", type: "many2many", relation: "res.groups" },
                },
                records: [
                    { id: 1, name: "Mitchell Admin", company_id: 1 },
                ],
            },
            "res.groups": {
                fields: {},
                records: [],
            },
            "res.company": {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    currency_id: { string: "Currency", type: "many2one", relation: "res.currency" },
                },
                records: [
                    { id: 1, display_name: "company 1", currency_id: 1 },
                ],
            },
            "decimal.precision": {
                fields: {},
                records: [],
            },
            "uom.uom": {
                fields: {},
                records: [],
            },
            "res.partner": {
                fields: {},
                records: [],
            },
            "res.country.state": {
                fields: {},
                records: [],
            },
            "res.country": {
                fields: {},
                records: [],
            },
            "account.tax": {
                fields: {},
                records: [],
            },
            "pos.session": {
                fields: {
                    journal_ids: { string: "Journals", type: "many2many", relation: "account.journal" },
                    name: { string: "Name", type: "char" },
                    user_id: { string: "User", type: "many2one", relation: "res.users" },
                    config_id: { string: "Config", type: "many2one", relation: "pos.config" },
                    start_at: { name: "Start at", type: "datetime" },
                    stop_at: { name: "Stop at", type: "datetime" },
                    sequence_number: { name: "Sequence", type: "integer" },
                    login_number: { name: "Login", type: "integer" },
                    state: { string: "State", type: "selection", selection: ["opened", "closed"] },
                    rescue: { string: "Rescue", type: "boolean" },
                    payment_method_ids: { string: "Payment Methods", type: "many2many", relation: "pos.payment.method" },
                },
                records: [
                    { id: 1, name: "Session 1", config_id: 1, user_id: 1, state: "opened" },
                ],
            },
            "pos.config": {
                fields: {
                    pricelist_id: { string: "Default pricelist", type: "many2one", relation: "product.pricelist" },
                    currency_id: { string: "Currency", type: "many2one", relation: "res.currency" },
                    company_id: { string: "Company", type: "many2one", relation: "res.company" },
                },
                records: [
                    { id: 1, pricelist_id: 1, currency_id: 1, company_id: 1 },
                ],
            },
            "product.pricelist": {
                fields: {},
                records: [
                    { id: 1 },
                ],
            },
            "product.pricelist.item": {
                fields: {},
                records: [],
            },
            "product.category": {
                fields: {},
                records: [],
            },
            "res.currency": {
                fields: {},
                records: [
                    { id: 1 },
                ],
            },
            "pos.category": {
                fields: {},
                records: [],
            },
            "product.product": {
                fields: {},
                records: [],
            },
            "account.bank.statement": {
                fields: {},
                records: [],
            },
            "account.journal": {
                fields: {},
                records: [],
            },
            "account.fiscal.position": {
                fields: {},
                records: [],
            },
            "account.fiscal.position.tax": {
                fields: {},
                records: [],
            },
            "pos.payment.method": {
                fields: {},
                records: [],
            },
        };
        this.session = {
            uid: 1,
            user_context: {
                allowed_company_ids: [1],
            },
        };
    },
}, function () {
    QUnit.test("basic rendering", async function (assert) {
        assert.expect(9);

        const pos = await createPointOfSale({
            data: this.data,
            session: this.session,
        });

        assert.containsOnce(pos, ".pos", "should have a Point of Sale container");
        assert.containsOnce(pos, ".loader", "should have a loading screen");
        assert.isVisible(pos, ".loader .progressbar",
            "should have a loading screen with a progress bar");

        await isPointOfSaleLoaded(pos);

        assert.isNotVisible(pos.$(".loader .progressbar"),
            "should have hidden the progress bar when loading is complete");

        // Chrome main parts
        assert.containsOnce(pos, ".pos-topheader", "should have a top navbar");
        assert.containsOnce(pos, ".pos-topheader .username",
            "should have a UsernameWidget in the top navbar");
        assert.containsOnce(pos, ".pos-topheader .order-selector",
            "should have an OrderSelectorWidget in the top navbar");
        assert.containsOnce(pos, ".pos-content .screens",
            "should have a screens container");
        assert.containsOnce(pos, ".pos-content .keyboard_frame",
            "should have a virtual keyboard container");

        pos.destroy();
    });

    QUnit.module("UsernameWidget", function() {
        QUnit.test("basic rendering", async function(assert) {
            assert.expect(1);

            const pos = await loadPointOfSale({
                data: this.data,
                session: this.session,
            });

            assert.strictEqual(pos.$(".pos-topheader .username").text().trim(), "Mitchell Admin");

            pos.destroy();
        });
    });

});
});
