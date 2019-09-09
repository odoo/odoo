odoo.define("point_of_sale.PointOfSaleTests", function (require) {
"use strict";

const { dom } = require("web.test_utils");
const { createPointOfSale, isPointOfSaleLoaded, loadPointOfSale, getPointOfSaleInstance } = require("point_of_sale.test_utils");
const { Orderline, Product } = require("point_of_sale.models");

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
                fields: {
                    name: { string: "Name", type: "char" },
                },
                records: [
                    { id: 1, name: "Units" },
                ],
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
                    available_pricelist_ids: { string: "Available Pricelists", type: "many2many", relation: "product.pricelist"},
                },
                records: [
                    { id: 1, pricelist_id: 1, currency_id: 1, company_id: 1, available_pricelist_ids: [1] },
                ],
            },
            "product.pricelist": {
                fields: {
                    discount_policy: {string: "Discount Policy", type: "selection"},
                    items: { string: "Items", type: "many2one", relation: "product.pricelist.item" },
                },
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
            "product.template": {
                fields: {},
                records: [],
            },
            "product.product": {
                fields: {
                    name: { string: "Name", type: "char" },
                    taxes_id: { string: "Taxes", type: "many2many", relation: "account.tax" },
                    sale_ok: { string: "Can be Sold", type: "boolean", default: true },
                    available_in_pos: { string: "Available in POS", type: "boolean" },
                    company_id: { string: "Company", type: "many2one", relation: "res.company" },
                    lst_price: { string: "Public Price", type: "float" },
                    standard_price: { string: "Cost", type: "float" },
                    categ_id: { string: "Product Category", type: "many2one", relation: "product.category" },
                    pos_categ_id: { string: "POS Category", type: "many2one", relation: "pos.category" },
                    barcode: { string: "Barcode", type: "char" },
                    default_code: { string: "Internal Reference", type: "char" },
                    to_weight: { string: "To Weight with Scale", type: "boolean" },
                    uom_id: { string: "Unit of Measure", type: "many2one", relation: "uom.uom" },
                    description_sale: { string: "Sales Description", type: "char" },
                    description: { string: "Description", type: "char" },
                    product_tmpl_id: { string: "Product Template", type: "many2one", relation: "product.template" },
                    tracking: { string: "Tracking", type: "selection", default: "none" },
                },
                records: [
                    { id: 1, name: "Chair", available_in_pos: true, company_id: 1, uom_id: 1 },
                    { id: 2, name: "Table", available_in_pos: true, company_id: 1, uom_id: 1 },
                    { id: 3, name: "Pencil", company_id: 1, uom_id: 1 },
                ],
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

    QUnit.module("OrderSelectorWidget", function() {
        QUnit.test("basic rendering", async function(assert) {
            assert.expect(6);

            const pos = await loadPointOfSale({
                data: this.data,
                session: this.session,
            });

            const orderSelector = ".pos-topheader .order-selector";

            assert.containsOnce(pos.$(orderSelector), ".orders",
                "should have an order list");
            assert.containsOnce(pos.$(orderSelector), ".neworder-button",
                "should have a new order button");
            assert.containsOnce(pos.$(orderSelector), ".deleteorder-button",
                "should have a delete order button");
            assert.containsOnce(pos.$(orderSelector), ".orders > .order-button",
                "should have 1 order by default");

            await dom.click(pos.$(orderSelector).find(".neworder-button"));
            assert.containsN(pos.$(orderSelector), ".orders > .order-button", 2,
                "should have 2 orders when clicking on new order button");

            await dom.click(pos.$(orderSelector).find(".deleteorder-button"));
            assert.containsOnce(pos.$(orderSelector), ".orders > .order-button",
                "should have 1 order when clicking on delete order button");

            pos.destroy();
        });
    });

    QUnit.module("ProductScreenWidget", function () {
        QUnit.test("basic rendering", async function (assert) {
            assert.expect(7);

            const pos = await loadPointOfSale({
                data: this.data,
                session: this.session,
            });

            const leftPanel = ".product-screen .leftpane";

            assert.containsOnce(pos, leftPanel,
                "should have a left panel");
            assert.containsOnce(pos.$(leftPanel), ".order",
                "left panel should have an Order");
            assert.containsOnce(pos.$(leftPanel), ".actionpad",
                "left panel should have an Actionpad");
            assert.containsOnce(pos.$(leftPanel), ".numpad",
                "left panel should have a Numpad");

            const rightPanel = ".product-screen .rightpane";
            assert.containsOnce(pos, rightPanel,
                "should have a right panel");
            assert.containsOnce(pos.$(rightPanel), ".rightpane-header",
                "should have ProductCategories header");
            assert.containsOnce(pos.$(rightPanel), ".product-list",
                "should have a ProductList");

            pos.destroy();
        });
    });

    QUnit.module("OrderWidget", function () {
        QUnit.test("basic rendering", async function (assert) {
            assert.expect(2);

            const pos = await loadPointOfSale({
                data: this.data,
                session: this.session,
            });

            const instance = getPointOfSaleInstance(pos);

            const order = instance.pos.get_order();
            const products = instance.pos.db.get_product_by_category(0);
            const product0 = new Product({}, products[0]);
            order.add_product(product0, { quantity: 1 });
            const product1 = new Product({}, products[1]);
            order.add_product(product1, { quantity: 1 });

            const orderContainer = ".product-screen .order-container";

            assert.containsOnce(pos.$(orderContainer), ".orderlines",
                "should have an orderline list");
            assert.containsN(pos.$(orderContainer), ".orderlines .orderline", 2,
                "should have 2 orderlines");

            pos.destroy();
        });

        QUnit.test("empty order", async function (assert) {
            assert.expect(3);

            const pos = await loadPointOfSale({
                data: this.data,
                session: this.session,
            });

            const orderContainer = ".product-screen .order-container";

            assert.containsNone(pos.$(orderContainer), ".orderlines",
                "shouldn't have any orderline list");
            assert.containsOnce(pos.$(orderContainer), ".order-empty",
                "should have an empty order splashscreen");
            assert.strictEqual(pos.$(orderContainer).find(".order-empty").text().trim(), "Your shopping cart is empty");

            pos.destroy();
        });
    });

    QUnit.module("ActionpadWidget", function () {
        QUnit.test("basic rendering", async function (assert) {
            assert.expect(3);

            const pos = await loadPointOfSale({
                data: this.data,
                session: this.session,
            });

            const actionpadContainer = ".product-screen .actionpad";

            assert.containsOnce(pos, actionpadContainer,
                "should have an Actionpad");
            assert.containsOnce(pos.$(actionpadContainer), ".set-customer",
                "should have a button to choose customer");
            assert.containsOnce(pos.$(actionpadContainer), ".pay",
                "should have a button to process payment");

            pos.destroy();
        });
    });

    QUnit.module("NumpadWidget", function () {
        QUnit.test("basic rendering", async function (assert) {
            assert.expect(8);

            const pos = await loadPointOfSale({
                data: this.data,
                session: this.session,
            });

            const numpadContainer = ".product-screen .numpad";

            assert.containsOnce(pos, numpadContainer,
                "should have a Numpad");
            assert.containsN(pos.$(numpadContainer), ".input-button.number-char", 11,
                "shoud have 11 'numeric' buttons (including the decimal mark)");
            assert.containsN(pos.$(numpadContainer), ".mode-button", 3,
                "should have 3 'mode' buttons");
            assert.containsOnce(pos.$(numpadContainer), ".mode-button[data-mode='quantity']",
                "should have a button to change quantity");
            assert.containsOnce(pos.$(numpadContainer), ".mode-button[data-mode='discount']",
                "should have a button to change discount");
            assert.containsOnce(pos.$(numpadContainer), ".mode-button[data-mode='price']",
                "should have a button to change price");
            assert.containsOnce(pos.$(numpadContainer), ".input-button.numpad-minus",
                "shoud have a 'sign' button");
            assert.containsOnce(pos.$(numpadContainer), ".input-button.numpad-backspace",
                "shoud have a 'backspace' button");

            pos.destroy();
        });
    });

    QUnit.module("ProductCategoriesWidget", function () {
        QUnit.test("basic rendering", async function (assert) {
            assert.expect(5);

            const pos = await loadPointOfSale({
                data: this.data,
                session: this.session,
            });

            const headerContainer = ".product-screen .rightpane-header";

            assert.containsOnce(pos, headerContainer,
                "should have ProductCategories");
            assert.containsOnce(pos.$(headerContainer), ".breadcrumbs",
                "should have a categories breadcrumb");
            assert.containsOnce(pos.$(headerContainer), ".breadcrumbs .breadcrumb-button.breadcrumb-home",
                "should have a 'home' categories' button");
            assert.containsOnce(pos.$(headerContainer), ".searchbox",
                "should have a categories search field");
            assert.containsOnce(pos.$(headerContainer), ".searchbox .search-clear.right",
                "should have a clear search field button");

            pos.destroy();
        });
    });

    QUnit.module("ProductListWidget", function () {
        QUnit.test("basic rendering", async function (assert) {
            assert.expect(2);

            const pos = await loadPointOfSale({
                data: this.data,
                session: this.session,
            });

            const listContainer = ".product-screen .product-list-container";

            assert.containsOnce(pos.$(listContainer), ".product-list",
                "should have a products list");
            assert.containsN(pos.$(listContainer), ".product-list .product", 2,
                "should have 2 products listed");

            pos.destroy();
        });

        QUnit.test("empty product list", async function (assert) {
            assert.expect(3);

            this.data["product.product"].records = [];

            const pos = await loadPointOfSale({
                data: this.data,
                session: this.session,
            });

            const listContainer = ".product-screen .product-list-container";

            assert.containsNone(pos.$(listContainer), ".product-list",
                "shouldn't have any products list");
            assert.containsOnce(pos.$(listContainer), ".product-list-empty",
                "should have an empty product list splashscreen");
            assert.strictEqual(pos.$(listContainer).find(".product-list-empty").text().trim(), "There are no products in this category.");

            pos.destroy();
        });
    });
});
});
