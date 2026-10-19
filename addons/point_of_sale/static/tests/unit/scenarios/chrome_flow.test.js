import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor, queryAll, press, advanceTime } from "@odoo/hoot-dom";
import { contains, getService } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp, createTestProduct } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";
import { PosNumberBufferPlugin } from "@point_of_sale/app/plugins/pos_number_buffer_plugin";

definePosModels();

test("FloatingOrderTour: floating orders preserve product quantities", async () => {
    const store = await setupAndMountPosApp();

    const order1 = store.getOrder();
    expect(order1.lines).toHaveLength(0);
    await Utils.clickDisplayedProduct("TEST");
    expect(order1.lines).toHaveLength(1);
    expect(order1.lines[0].qty).toBe(1);
    await Utils.clickDisplayedProduct("TEST");
    expect(order1.lines[0].qty).toBe(2);
    await contains(".pos-leftheader .list-plus-btn").click();
    await animationFrame();
    const order2 = store.getOrder();
    expect(order2).not.toBe(order1);
    await Utils.clickDisplayedProduct("TEST 2");
    expect(order2.lines).toHaveLength(1);
    expect(order2.lines[0].qty).toBe(1);
    await Utils.clickDisplayedProduct("TEST 2");
    expect(order2.lines[0].qty).toBe(2);
    if (Utils.isMobile()) {
        await contains(".list-container-items button:has([data-icon='arrow_drop_down'])").click();
        await animationFrame();
        const floatingBtns = queryAll(".list-container-items .floating-order-container .btn");
        await contains(floatingBtns[0]).click();
    } else {
        const floatingBtns = queryAll(".list-container-items .floating-order-container .btn");
        await contains(floatingBtns[0]).click();
    }
    await animationFrame();
    expect(store.getOrder()).toBe(order1);
    expect(order1.lines[0].qty).toBe(2);
    await waitFor(".product-screen");
    if (Utils.isMobile()) {
        await contains(".list-container-items button:has([data-icon='arrow_drop_down'])").click();
        await animationFrame();
        const floatingBtns = queryAll(".list-container-items .floating-order-container .btn");
        await contains(floatingBtns[1]).click();
    } else {
        const floatingBtns = queryAll(".list-container-items .floating-order-container .btn");
        await contains(floatingBtns[1]).click();
    }
    await animationFrame();
    expect(store.getOrder()).toBe(order2);
    expect(order2.lines[0].qty).toBe(2);
    await Utils.ensurePane("left");
    if (Utils.isMobile()) {
        await contains(".product-screen .mobile-more-button").click();
    } else {
        await contains(".product-screen .more-btn").click();
    }
    await animationFrame();
    await press("9");
    await animationFrame();
    await advanceTime(200);
    await Utils.cancelDialog();
    await waitFor(".product-screen");
    expect(order2.lines[0].qty).toBe(2);
    const numberBuffer = getService(PosNumberBufferPlugin);
    expect(numberBuffer.get()).toBe("");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");

    await Utils.clickPaymentMethod("Cash");
    await Utils.clickValidatePayment();

    await Utils.clickNextOrder();
});

test.tags("desktop");
test("test_click_all_orders_keep_customer: all orders keeps the selected customer", async () => {
    const store = await setupAndMountPosApp();

    const partner = store.models["res.partner"].get(3);

    await Utils.selectCustomer(partner.name);
    await animationFrame();

    await Utils.checkSelectedCustomer(partner.name);
    await Utils.clickPartnerButton();
    await contains(
        `.partner-info:contains("${partner.name}") button:has([data-icon='menu'])`
    ).click();
    await animationFrame();
    await contains('.dropdown-item:contains("All Orders")').click();
    await animationFrame();
    await waitFor(".ticket-screen");

    await Utils.clickRegister();
    await waitFor(".product-screen");
    await Utils.checkSelectedCustomer(partner.name);
});

test("PosCategoriesOrder: pos categories keep sequence and hierarchy", async () => {
    const store = await setupAndMountPosApp();

    // Set existing categories to high sequence so new ones come first
    store.models["pos.category"].getAll().forEach((c) => (c.sequence = 100));

    store.models["pos.category"].create({
        id: 100,
        name: "AAA",
        parent_id: false,
        child_ids: [],
        sequence: 1,
        has_image: false,
        color: 0,
        hour_until: 0,
        hour_after: 24,
    });
    const aab = store.models["pos.category"].create({
        id: 101,
        name: "AAB",
        parent_id: false,
        child_ids: [],
        sequence: 2,
        has_image: false,
        color: 0,
        hour_until: 0,
        hour_after: 24,
    });
    store.models["pos.category"].create({
        id: 102,
        name: "AAC",
        parent_id: false,
        child_ids: [],
        sequence: 3,
        has_image: false,
        color: 0,
        hour_until: 0,
        hour_after: 24,
    });
    const aax = store.models["pos.category"].create({
        id: 103,
        name: "AAX",
        parent_id: 101,
        child_ids: [],
        sequence: 4,
        has_image: false,
        color: 0,
        hour_until: 0,
        hour_after: 24,
    });
    const aay = store.models["pos.category"].create({
        id: 104,
        name: "AAY",
        parent_id: 103,
        child_ids: [],
        sequence: 5,
        has_image: false,
        color: 0,
        hour_until: 0,
        hour_after: 24,
    });
    aab.child_ids = [aax];
    aax.child_ids = [aay];

    createTestProduct(store, { id: 7100, name: "Product in AAB and AAX", categoryId: 101 });
    store.models["product.template"].get(7100).pos_categ_ids = [
        store.models["pos.category"].get(101),
        store.models["pos.category"].get(103),
    ];
    createTestProduct(store, { id: 7101, name: "Product in AAA Catg", categoryId: 100 });
    createTestProduct(store, { id: 7102, name: "Product in AAC Catg", categoryId: 102 });
    createTestProduct(store, { id: 7103, name: "Product in AAY Catg", categoryId: 104 });
    await animationFrame();

    await waitFor(".category-list");
    const categoryButtons = queryAll(".category-button span");
    const names = categoryButtons.map((el) => el.textContent.trim());
    const aaaIdx = names.indexOf("AAA");
    const aabIdx = names.indexOf("AAB");
    const aacIdx = names.indexOf("AAC");
    expect(aaaIdx).not.toBe(-1);
    expect(aabIdx).not.toBe(-1);
    expect(aacIdx).not.toBe(-1);
    expect(aaaIdx < aabIdx).toBe(true);
    expect(aabIdx < aacIdx).toBe(true);

    const aabBtn = [...document.querySelectorAll(".category-button span")].find(
        (el) => el.textContent.trim() === "AAB"
    );
    await contains(aabBtn.closest(".category-button")).click();
    await animationFrame();

    await waitFor('article.product .product-name:contains("Product in AAB and AAX")');

    const subCats = queryAll(".category-button span").map((el) => el.textContent.trim());
    expect(subCats).toInclude("AAX");

    const aaxBtn = [...document.querySelectorAll(".category-button span")].find(
        (el) => el.textContent.trim() === "AAX"
    );
    await contains(aaxBtn.closest(".category-button")).click();
    await animationFrame();

    const subCats2 = queryAll(".category-button span").map((el) => el.textContent.trim());
    expect(subCats2).toInclude("AAY");
});

test("test_preset_customer_selection: selecting a customer with address preset", async () => {
    const store = await setupAndMountPosApp({
        use_presets: true,
        default_preset_id: 4,
        available_preset_ids: [4],
    });

    const partner = store.models["res.partner"].create({
        id: 9201,
        name: "Partner Full",
        street: "77 Santa Barbara Rd",
        city: "Pleasant Hill",
        zip: "94523",
        address: "77 Santa Barbara Rd Pleasant Hill",
        barcode: false,
        email: false,
        phone: false,
        lang: "en_US",
        parent_name: false,
        fiscal_position_id: false,
        invoice_emails: "",
        property_product_pricelist: false,
        write_date: "2025-07-03 12:38:12",
    });
    await animationFrame();
    await Utils.cancelDialog();
    await Utils.clickPartnerButton();
    await waitFor(".partner-list");
    if (Utils.isMobile()) {
        await contains(".oi.undefined").click();
        await animationFrame();
    }
    await contains(".modal-header input").edit("Partner Full");
    await animationFrame();
    await contains(`.partner-info:contains("Partner Full")`).click();
    await animationFrame();

    expect(store.getOrder().partner_id.id).toBe(partner.id);

    await Utils.clickOrders();
    await waitFor(".ticket-screen");

    if (!Utils.isMobile()) {
        const addressCell = document.querySelector(".address-cell");
        expect(addressCell.textContent).toInclude("77 Santa Barbara Rd Pleasant Hill");
    }
});

test("PosCustomerAllFieldsDisplayed: partner fields displayed and searchable", async () => {
    const store = await setupAndMountPosApp();

    store.models["res.partner"].create({
        id: 9310,
        name: "John Doe",
        street: "1 street of astreet",
        city: "Acity",
        zip: "26432685463",
        phone: "9898989899",
        email: "john@doe.com",
        barcode: false,
        lang: "en_US",
        write_date: "2025-07-03 12:38:12",
        property_product_pricelist: false,
        parent_name: false,
        address: "1 street of astreet Acity 26432685463",
        invoice_emails: "",
        fiscal_position_id: false,
    });

    await Utils.clickPartnerButton();
    await waitFor(".partner-list");

    const partnerInfo = [...document.querySelectorAll(".partner-info")].find((el) =>
        el.textContent.includes("John Doe")
    );
    expect(partnerInfo).not.toBe(null);
    expect(partnerInfo.textContent).toInclude("1 street of astreet");
    expect(partnerInfo.textContent).toInclude("9898989899");
    expect(partnerInfo.textContent).toInclude("john@doe.com");

    await contains(".modal .btn-secondary").click();
    await animationFrame();

    await Utils.clickPartnerButton();
    await waitFor(".partner-list");
    if (Utils.isMobile()) {
        await contains(".oi.undefined").click();
        await animationFrame();
    }

    await contains(".partner-list input, .modal-dialog .input-group input").edit("John Doe");
    await animationFrame();
    const result1 = [...document.querySelectorAll(".partner-info")].find((el) =>
        el.textContent.includes("John Doe")
    );
    expect(result1).not.toBe(null);

    await contains(".partner-list input, .modal-dialog .input-group input").edit("9898989899");
    await animationFrame();
    const result2 = [...document.querySelectorAll(".partner-info")].find((el) =>
        el.textContent.includes("John Doe")
    );
    expect(result2).not.toBe(null);

    await contains(".partner-list input, .modal-dialog .input-group input").edit("j%hn d%e");
    await animationFrame();
    const result3 = [...document.querySelectorAll(".partner-info")].find((el) =>
        el.textContent.includes("John Doe")
    );
    expect(result3).not.toBe(null);
});

test("customer_display_shows_qr_popup: customer display QR code popup", async () => {
    await setupAndMountPosApp();

    await contains(
        ".pos-leftheader button:has([data-icon='menu']), .pos-topheader button:has([data-icon='menu'])"
    ).click();
    await animationFrame();

    await contains('.o_pos_burger_menu_buttons button:contains("Customer Display")').click();
    await animationFrame();

    await waitFor(".modal");

    if (Utils.isMobile()) {
        const deviceBtn = document.querySelector(".o-overlay-item .modal .modal-footer a");
        const url = deviceBtn.href;
        expect(url).not.toInclude("undefined");
        expect(new URL(url)).toBeInstanceOf(URL);
    } else {
        await waitFor('.modal .btn:contains("This Device")');
        await contains('.modal .btn:contains("Display Qr")').click();
        await animationFrame();
        await waitFor(".modal img, .modal canvas, .modal svg");
    }
});
