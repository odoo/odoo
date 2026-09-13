import { expect } from "@odoo/hoot";
import { animationFrame, waitFor, queryFirst, queryAll, delay } from "@odoo/hoot-dom";
import { contains, getService } from "@web/../tests/web_test_helpers";

export function isMobile() {
    return getService("ui").isSmall;
}

export async function mountSelfOrderApp(store) {
    await animationFrame();
}

export async function clickOrderNow() {
    await contains(".btn:contains('Order Now'), .btn:contains('Order now')").click();
    await animationFrame();
}

export async function clickMyOrder() {
    await contains(".btn:contains('My Order'), .btn:contains('My Orders')").click();
    await animationFrame();
}

export async function checkIsClosed() {
    await waitFor(".o-self-closed");
}

export async function checkIsOpened() {
    expect(".o-self-closed").toHaveCount(0);
}

export async function checkIsNoBtn(text) {
    expect(`.btn:contains('${text}')`).toHaveCount(0);
}

export async function checkBtn(text) {
    await waitFor(`.btn:contains('${text}')`);
}

export async function checkIsDisabledBtn(text) {
    await waitFor(`button.disabled:contains("${text}")`);
}

export async function selectLocation(name) {
    await contains(`.o_self_eating_location_box .preset_btn:contains('${name}')`).click();
    await animationFrame();
}

export async function selectFloor(floor) {
    await contains(
        `.self_order_pills_selection_popup .preset_date_buttons:contains('${floor}')`
    ).click();
    await animationFrame();
}

export async function selectTable(table) {
    await contains(`.self_order_pills_selection_popup .option-item:contains('${table}')`).click();
    await animationFrame();
    await contains(`.self_order_pills_selection_popup .btn-primary:contains('Confirm')`).click();
    await animationFrame();
}

export async function selectTimeSlot() {
    await waitFor(".self_order_pills_selection_popup");
    await contains(".self_order_pills_selection_popup .option-item:first").click();
    await animationFrame();
    await contains(".self_order_pills_selection_popup .btn-primary:contains('Confirm')").click();
    await animationFrame();
}

export async function selectSpecificSlot(slotValue) {
    await waitFor(".self_order_pills_selection_popup");
    await contains(
        `.self_order_pills_selection_popup .option-item:contains('${slotValue}')`
    ).click();
    await animationFrame();
    await contains(".self_order_pills_selection_popup .btn-primary:contains('Confirm')").click();
    await animationFrame();
}

export async function checkSlotUnavailable(slotValue) {
    await waitFor(".self_order_pills_selection_popup");
    const slots = queryAll(".self_order_pills_selection_popup .option-item").map((slot) =>
        slot.textContent.trim()
    );
    if (slots.includes(slotValue)) {
        throw new Error(`${slotValue} should not be available`);
    }
}

export async function clickProduct(name) {
    await contains(`.o_self_product_card span:contains('${name}')`).click();
    await animationFrame();
}

export async function clickProductInfo(name) {
    await contains(`.o_self_product_card:contains('${name}') .product_info_icon`).click();
    await animationFrame();
}

export async function clickCategory(name) {
    await contains(`.category_btn:contains('${name}')`).click();
    await animationFrame();
}

export async function checkCategoryBtn(name) {
    await waitFor(`.category_btn:contains('${name}')`);
}

export function checkIsNoCategoryBtn(name) {
    expect(`.category_btn:contains('${name}')`).toHaveCount(0);
}

export function checkIsNoChildCategoryBtn(name) {
    expect(`.child_category_btn:contains('${name}')`).toHaveCount(0);
}

export async function clickChildCategory(name) {
    await contains(`.child_category_btn:contains('${name}')`).click();
    await animationFrame();
}

export async function waitProduct(name) {
    await waitFor(`.o_self_product_card span:contains('${name}')`);
}

export async function checkProductQty(name, qty) {
    await waitFor(
        `.o_self_product_list_page .o_self_product_card:has(.self_order_product_name:contains('${name}')) .badge:contains('${qty}')`
    );
}

export async function checkOrderTotal(amount) {
    await waitFor(
        `.o_self_product_list_page .o_self_shadow_bottom .o-so-tabular-nums:contains('${amount}')`
    );
}

export async function checkReferenceNotInProductName(productName, reference) {
    await waitFor(
        `.o_self_product_card span:contains('${productName}'):not(:contains("${reference}"))`
    );
}

export function isProductDisplayed(productName, isOutOfStock = false) {
    let selector = `.o_self_product_card:has(span:contains('${productName}'))`;
    if (isOutOfStock) {
        selector += `:has(div:contains('Out of stock'))`;
    }
    return waitFor(selector);
}

export async function isProductNotDisplayed(productName) {
    expect(`.o_self_product_card:has(span:contains('${productName}'))`).toHaveCount(0);
}

export function checkNthProduct(n, name) {
    expect(
        `.product_list .o_self_product_card:nth-child(${n}) span:contains('${name}')`
    ).toHaveCount(1);
}

export async function setupAttribute(attributes) {
    for (const attr of attributes) {
        await contains(
            `h2:contains("${attr.name}") + div.row button:contains("${attr.value}")`
        ).click();
        await animationFrame();
    }
}

export async function selectAttributeValue(value) {
    await contains(`.self_order_attribute_selection button:contains('${value}')`).click();
    await animationFrame();
}

export async function selectNthAttributeValue(n, attributeName) {
    const scope = attributeName ? `h2:contains(${attributeName}) + ` : "";
    await contains(`${scope}.self_order_attribute_selection div:nth-child(${n}) button`).click();
    await animationFrame();
}

export function checkAttributeShown(name) {
    expect(`div h2:contains('${name}')`).toHaveCount(1);
}

export function checkAttributeIsOptional(name) {
    expect(`h2:contains('${name}') .badge`).toHaveCount(0);
}

export function checkAttributeValueCount(count) {
    expect(".self_order_attribute_selection button").toHaveCount(count);
}

export function checkAttributeGroups(groupCount, valuePerGroup) {
    expect(`.self_order_attribute_selection:has(button:count(${valuePerGroup}))`).toHaveCount(
        groupCount
    );
}

export function checkAttributeGroupHasValues(values) {
    let selector = ".self_order_attribute_selection";
    for (const value of values) {
        selector += `:has(button:contains('${value}'))`;
    }
    expect(selector).toHaveCount(1);
}

export async function attributeHasColorDot(attribute) {
    await waitFor(`div:has(span:contains("${attribute}")) ~ div.rounded-5`);
}

export async function attributeHasImage(attribute) {
    await waitFor(`div:has(span:contains("${attribute}")) ~ img.rounded-4`);
}

export async function clickDiscard() {
    await contains(".btn.btn-link [data-icon='close_small']").click();
    await animationFrame();
}

export async function clickComboProduct(productName) {
    await contains(`.combo_product_box span:contains('${productName}')`).click();
    await animationFrame();
}

export async function setupCombo(products) {
    for (const product of products) {
        await clickComboProduct(product.product);
        if (product.attributes.length > 0) {
            await setupAttribute(product.attributes);
            await clickBtn("Next");
        }
    }
}

export async function clickNext() {
    await clickBtn("Next");
}

export async function clickAddToCart() {
    await clickBtn("Add to cart");
}

export async function clickCancelPopup() {
    await contains(".btn.btn-cancel").click();
    await animationFrame();
}

export async function verifyItemHasPriceBadge(productName, price) {
    await waitFor(
        `.combo_product_box:has(span:contains('${productName}')) .badge:contains('+ $ ${price}')`
    );
}

export async function verifyItemHasExtraBadge(productName, price) {
    await waitFor(
        `.combo_product_box:has(span:contains('${productName}')) .badge:contains('Extra: $ ${price}')`
    );
}

export async function verifyItemHasNoExtraBadge(productName) {
    const box = queryFirst(`.combo_product_box:has(span:contains('${productName}'))`);
    if (box) {
        const badge = box.querySelector(".badge");
        if (badge && badge.textContent.includes("Extra")) {
            throw new Error(`Product '${productName}' should not have Extra badge`);
        }
    }
}

export async function verifyConfirmationPageShown() {
    await waitFor(".o_self_combo_confirmation:contains('Validate your selection')");
}

export async function verifyConfirmationHasExtraPrice(productName) {
    await waitFor(".o_self_combo_confirmation .badge:contains('Extra:')");
}

export async function increaseComboItemQty(productName, qty) {
    await waitFor(`.combo_product_box span:contains("${productName}")`);
    for (let i = 1; i < qty; i++) {
        await waitFor(`.item_qty_container .o-so-tabular-nums:contains("${i}")`);
        await contains(".item_qty_container button:eq(1)").click();
        await animationFrame();
    }
}

export async function clickCheckout() {
    await clickBtn("Checkout");
}

export async function clickOrder() {
    await clickBtn("Order");
}

export async function clickPay() {
    await clickBtn("Pay");
}

export async function clickBackFromCart() {
    await contains(".btn.btn-back").click();
    await animationFrame();
}

export async function clickBackFromProduct() {
    if (isMobile()) {
        await contains("[data-icon='chevron_backward']").click();
        await animationFrame();
    } else {
        await clickBtn("Back");
    }
}

// `name` scopes the click to the cart line of that product; without it the
// first matching button of the page is used (fine when the cart has one line).
async function clickCartItemBtn(name, icon) {
    const scope = name ? `.product-cart-item:has(div:contains('${name}'))` : ".btn";
    await contains(`${scope} [data-icon='${icon}']`).click();
    await animationFrame();
}

export async function increaseCartItemQty(name) {
    await clickCartItemBtn(name, "add");
}

export async function decreaseCartItemQty(name) {
    await clickCartItemBtn(name, "remove");
}

export async function removeCartItem(name) {
    await clickCartItemBtn(name, "delete");
}

export function checkNoOrderNote() {
    expect(".order-note").toHaveCount(0);
}

export async function clickCancelFromProductList() {
    await contains(".btn.btn-cancel").click();
    await animationFrame();
    await contains(".btn.btn-primary:contains('Cancel Order')").click();
    await animationFrame();
}

export async function clickCancelOrder() {
    await contains('.o_self_cart_page .btn:contains("Cancel")').click();
    await animationFrame();
    await contains(".modal-dialog .btn:contains('Cancel Order')").click();
    await animationFrame();
}

export async function checkProductInCart(name, price, quantity = "1") {
    await waitFor(
        `.product-cart-item:has(div:contains("${name}")):has(div:contains("${quantity}")):has(div .o-so-tabular-nums:contains("${price}"))`
    );
}

export async function checkAttributeInCart(productName, attributes) {
    let selector = `.product-cart-item div:contains("${productName}")`;
    for (const attr of attributes) {
        selector += `:has(div:contains("${attr.name}: ${attr.value}"))`;
    }
    await waitFor(selector);
}

export async function checkComboInCart(comboName, products) {
    for (const product of products) {
        let selector = `.product-cart-item div:contains("${comboName}"):has(div:contains(${product.product}))`;
        if (product.attributes.length > 0) {
            for (const attr of product.attributes) {
                selector += `:has(div:contains("${attr.name}") div:contains("${attr.value}"))`;
            }
        }
        await waitFor(selector);
    }
}

export async function checkTotalPrice(price) {
    await waitFor(`.order-price :contains(Total):contains(${price})`);
}

export async function checkNoTableSelector() {
    expect(".self_order_popup_table").toHaveCount(0);
}

export async function fillInput(placeholder, value) {
    await contains(`input[placeholder="${placeholder}"]`).edit(value);
    await animationFrame();
}

export async function clickOrderNoteBtn() {
    await contains(".order-note").click();
    await animationFrame();
}

export async function clickTextArea() {
    await contains(".modal:not(.o_inactive_modal) textarea").click();
    await animationFrame();
}

export async function typeNote(text) {
    await contains(".modal:not(.o_inactive_modal) textarea").edit(text);
    await animationFrame();
}

export async function clickApply() {
    await clickBtn("Apply");
}

export async function clickOk() {
    await clickBtn("Ok");
}

export async function clickClose() {
    await clickBtn("Close");
}

export async function clickContinue() {
    await clickBtn("Continue");
}

export async function clickMyOrders() {
    await clickBtn("My Orders");
}

export async function clickPresetBtn() {
    await contains("button.preset-btn").click();
    await animationFrame();
}

export async function checkPreset(name) {
    await waitFor(`button.preset-btn:contains('${name}')`);
}

export async function isCartPageShown() {
    await waitFor(".o_self_cart_page");
}

export async function checkConfirmationPage() {
    await waitFor(".confirmation-page");
}

export async function checkConfirmationString(timingPreset = false) {
    if (timingPreset) {
        await waitFor('.confirmation-block h1:contains("Order for")');
    } else {
        await waitFor('.confirmation-block h1:contains("We\'re preparing your order!")');
    }
}

export async function checkOrderNumberShown() {
    await waitFor(".tracking-number");
}

export async function checkOrderNumberIs(prefix, num) {
    const span = queryFirst("span.tracking-number");
    const text = span?.textContent || "";
    if (!text.startsWith(prefix) || !text.endsWith(num)) {
        throw new Error(
            `Order number '${text}' does not start with '${prefix}' and end with '${num}'`
        );
    }
}

export async function confirmDialog(buttonText) {
    await waitFor(".modal");
    if (buttonText) {
        await contains(`.modal .btn:contains("${buttonText}")`).click();
    } else {
        await contains(".modal .btn-primary").click();
    }
    await animationFrame();
}

export async function cancelDialog() {
    await waitFor(".modal");
    await contains(".modal .btn-secondary").click();
    await animationFrame();
}

export async function dialogBodyIs(text) {
    await waitFor(`.modal-body:contains("${text}")`);
}

export async function clickNumpad(digit) {
    await contains(`.numpad button:contains("${digit}")`).click();
    await animationFrame();
}

export async function hasBtn(buttonName) {
    waitFor(`.btn:contains(${buttonName})`);
}

export async function clickBtn(buttonName) {
    await contains(`.btn:contains('${buttonName}')`).click();
    await animationFrame();
}

export async function checkMissingRequiredsExists() {
    await waitFor("div.missing_required_details");
}

export async function clickMissingRequireds() {
    await contains("div.missing_required_details button").click();
    await animationFrame();
}

export function negateStep(text) {
    expect(`.btn:contains('${text}')`).toHaveCount(0);
}

export async function openLanguageSelector() {
    await contains(".o_self_language_selector").click();
    await animationFrame();
}

export async function changeLanguage(language) {
    await openLanguageSelector();
    await contains(`.self_order_language_popup .btn:contains(${language})`).click();
    await waitFor(`.o_self_language_selector:contains(${language})`);
    await animationFrame();
}

export async function checkLanguageSelected(language) {
    await waitFor(`.o_self_language_selector:contains("${language}")`);
}

export async function checkCountryFlagShown(country_code) {
    await waitFor(`.o_self_language_selector > img[src*=${country_code}]`);
}

export async function checkCarouselAutoPlaying() {
    await waitFor(".carousel-item.active");
    const firstSlideHtml = queryFirst(".carousel-item.active")?.outerHTML;
    await delay(250);
    const currentSlideHtml = queryFirst(".carousel-item.active")?.outerHTML;
    if (firstSlideHtml === currentSlideHtml) {
        throw new Error("Slideshow is not working. Slide should change in all self ordering mode.");
    }
}

export async function selectFirstAddressDropdown() {
    await contains(".o-autocomplete--dropdown-menu .dropdown-item").click();
    await animationFrame();
}

export async function clickTakeaway() {
    await contains("button:contains('Takeaway')").click();
    await animationFrame();
}

export async function checkAddressError() {
    await waitFor("p.text-danger:contains('Delivery isn\u2019t available')");
}

export async function setProductAvailability(store, productName, value) {
    const product = store.models["product.product"].find((p) => p.name === productName);
    const productTmpl = store.models["product.template"].find((p) => p.name === productName);
    if (!product) {
        throw new Error(`Product '${productName}' not found.`);
    }
    product.self_order_available = value;
    productTmpl.self_order_available = value;
    await animationFrame();
}

export async function isProductListPageShown() {
    await waitFor(".o_self_product_list_page");
}

export async function checkQRCodeGenerated() {
    await waitFor("h1:contains('Scan the QR code to pay')");
}

export async function clickBack() {
    await contains(".btn.btn-back").click();
    await animationFrame();
}

export const page = {
    isLanding: () => waitFor(".o_pos_landing_footer"),
    isEatingLocation: () => waitFor(".o_self_eating_location_box"),
    isProductList: () => waitFor(".o_self_product_list_page"),
    isProduct: () => waitFor(".o_self_product_page"),
    isCombo: () => waitFor(".o_self_combo_page"),
    isOptionalProduct: () => waitFor(".o_self_optional_product_page"),
    isConfirmation: () => waitFor(".confirmation-page"),
};

export async function clickProductCard(productName) {
    await contains(`.o_self_product_card span:contains('${productName}')`).click();
    await animationFrame();
}

export function expectProductCardQty(productName, qty) {
    expect(
        `.o_self_product_card:has(.self_order_product_name:contains(${productName})):has(.badge:contains(${qty}))`
    ).toBeVisible();
}

export async function setupAttributeNew(attributes, clickAddToCart = true) {
    for (const { name, value } of attributes) {
        await contains(
            `.o_self_product_page_attributes h2:contains("${name}") + div.row button:contains("${value}")`
        ).click();
        await animationFrame();
    }
    if (clickAddToCart) {
        await contains(".btn:contains('Add to cart')").click();
        await animationFrame();
    }
}

export async function setupComboNew(products) {
    for (const { product, qty, attributes } of products) {
        await contains(`.o_self_product_card span:contains('${product}')`).click();
        await animationFrame();
        if (qty && qty > 1) {
            for (let i = 1; i < qty; i++) {
                await contains(`.o_self_product_card span:contains('${product}')`).click();
                await animationFrame();
            }
        }
        if (attributes?.length > 0) {
            await setupAttributeNew(attributes, false);
        }
        await contains(".btn:contains('Next')").click();
        await animationFrame();
    }
    await contains(".btn:contains('Add to cart')").click();
    await animationFrame();
}

export async function hasCartItem({ productName, qty, price, attributes, combos }) {
    let selector = `.product-cart-item:has(div:contains(${productName}))`;
    if (qty) {
        selector += `:has(.btn-group .o-so-tabular-nums:contains(${qty}))`;
    }
    if (price) {
        selector += `:has(.line-price:contains(${price}))`;
    }
    for (const attr of attributes || []) {
        selector += `:has(div:contains(${attr}))`;
    }
    for (const comboLine of combos || []) {
        selector += `:has(div:contains(${comboLine}))`;
    }
    await waitFor(selector);
    expect(selector).toBeVisible();
}

export async function cartTotalIs(total) {
    const selector = `.order-price span:contains(${total})`;
    await waitFor(selector);
    expect(selector).toBeVisible();
}

export async function confirmCart(products, total) {
    const cartItemAsserts = products.map((p) => hasCartItem(p));
    if (total !== undefined) {
        cartItemAsserts.push(cartTotalIs(total));
    }
    await Promise.all(cartItemAsserts);
}

export async function checkPaymentPage() {
    await waitFor(".payment-page");
}
