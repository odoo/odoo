import { browser } from '@web/core/browser/browser';
import { _t } from '@web/core/l10n/translation';
import { rpc } from "@web/core/network/rpc";
import { createElementWithContent, setElementContent } from '@web/core/utils/html';
import { redirect } from '@web/core/utils/urls';
import { markup } from "@odoo/owl";

/**
 * Updates both navbar cart
 * @param {Object} data
 * @return {void}
 */
function updateCartNavBar(data) {
    browser.sessionStorage.setItem('website_sale_cart_quantity', data.cart_quantity);
    // Mobile and Desktop elements have to be updated.
    const cartQuantityElements = document.querySelectorAll('.my_cart_quantity');
    for(const cartQuantityElement of cartQuantityElements) {
        if (data.cart_quantity === 0) {
            cartQuantityElement.classList.add('d-none');
        } else {
            const cartIconElement = document.querySelector('li.o_wsale_my_cart');
            cartIconElement.classList.remove('d-none');
            cartQuantityElement.classList.remove('d-none');
            cartQuantityElement.classList.add('o_mycart_zoom_animation');
            setTimeout(() => {
                cartQuantityElement.textContent = data.cart_quantity;
                cartQuantityElement.classList.remove('o_mycart_zoom_animation');
            }, 300);
        }
    }

    const cartLines = document.querySelectorAll('.js_cart_lines');
    cartLines[0]?.insertAdjacentHTML('beforebegin', data['website_sale.cart_lines']);
    cartLines.forEach(el => el.remove());

    updateCartSummary(data);

    if (!data.cart_has_blocking_alerts) {
        document.querySelector("a[name='website_sale_main_button']")?.classList.remove('disabled');
    } else {
        document.querySelector("a[name='website_sale_main_button']")?.classList.add('disabled');
    }
}

/**
 * Update the cart summary.
 *
 * @param {Object} data
 * @return {void}
 */
function updateCartSummary(data) {
    if (data['website_sale.shorter_cart_summary']) {
        const shorterCartSummaryEl = document.querySelector('.o_wsale_shorter_cart_summary');
        const newShorterCartSummaryEl = createElementWithContent(
            'div', data['website_sale.shorter_cart_summary'],
        );
        shorterCartSummaryEl.replaceWith(...newShorterCartSummaryEl.childNodes);
    }
    if (data['website_sale.total']) {
        document.querySelectorAll('div.o_cart_total').forEach(
            div => div.innerHTML = data['website_sale.total']
        );
    }
}

/**
 * Update the quick reorder side panel.
 *
 * @param {Object} data
 * @return {void}
 */
function updateQuickReorderSidebar(data) {
    const quickReorderButton  = document.getElementById('quick_reorder_button');
    document.querySelectorAll('.o_wsale_quick_reorder_line_group').forEach(el => el.remove());
    if (data['website_sale.quick_reorder_history'].trim()) {
        document.querySelector('#quick_reorder_sidebar .offcanvas-body').insertAdjacentHTML(
            'afterbegin', data['website_sale.quick_reorder_history']
        );
        quickReorderButton.removeAttribute('disabled');
        quickReorderButton.parentElement.title = "";
    } else {
        quickReorderButton.click();
        quickReorderButton.setAttribute('disabled', 'true');
        quickReorderButton.parentElement.title = _t("No previous products available for reorder.");
    }
}

/**
 * Replace the content of the current element with the content of the element
 * matching `selector` inside `newRoot`. No-op if either side of the swap
 * can't be found.
 *
 * @param {Element} newRoot - root element containing the freshly fetched markup
 * @param {string} selector - selector of the element to read from `newRoot`
 * @param {Object} [optionalParams={}]
 * @param {function(Element): void} [optionalParams.postUpdate] - callback to
 *  alter the current element once its content has been updated.
 * @param {string} [optionalParams.currSelector] - selector of the current
 *  element, if different from `selector`
 * @return {void}
 */
function updateElementContent(
    newRoot,
    selector,
    { postUpdate = () => {}, currSelector = null } = {},
) {
    let newEl = newRoot.querySelector(selector);
    const currentSelector = currSelector ?? selector;
    const currentEl = document.querySelector(currentSelector);
    if (newEl && currentEl) {
        currentEl.replaceChildren(...newEl.childNodes);
        postUpdate(currentEl);
    }
}

/**
 * Re-apply the "expanded" state of the accordion buttons that were open before the update.
 *
 * @param {Element} sidebar
 * @param {Set<string>} expandedTargets - set of previously expanded accordion target
 * @return {void}
 */
function restoreExpandedAccordions(sidebar, expandedTargets) {
    sidebar.style.marginTop = "0.3rem"; // margin is needed to avoid sidebar flicker.
    const buttonsToExpand = [...sidebar.querySelectorAll(".accordion-button")].filter(
        (button) => expandedTargets.has(button.dataset.bsTarget)
    );
    for (const button of buttonsToExpand) {
        button.ariaExpanded = true;
        button.classList.remove("collapsed");
        sidebar.querySelector(button.dataset.bsTarget)?.classList.add("show");
    }
}

async function updateShopContent(interaction, {
    url,
    searchParams,
}) {
    const targetUrl = `${url.pathname}?${searchParams.toString()}`;
    const expandedTargets = new Set(
        [...document.querySelectorAll(".accordion-item .accordion-button[aria-expanded=true]")]
            .map((el) => el.dataset.bsTarget)
    );
    const productGridWrapper = document.querySelector('.o_wsale_products_grid_table_wrapper');
    productGridWrapper?.classList?.add('opacity-50');

    try {
        const paramsObject = Object.fromEntries(searchParams.entries());
        const headerEl = document.querySelector("#o_wsale_products_header");
        if (headerEl){
            paramsObject.category = headerEl.dataset.categoryId;
        }
        const data = await interaction.waitFor(rpc('/shop/reload', paramsObject));
        const updatedShopPage = createElementWithContent("div", markup(data.html));
        const shopPageEl = document.querySelector('.o_wsale_products_page');
        interaction.services['public.interactions'].stopInteractions(shopPageEl);

        updateElementContent(
            updatedShopPage,
            "#products_grid_before",
            {
                postUpdate: (el) => restoreExpandedAccordions(el, expandedTargets)
            }
        );

        updateElementContent(updatedShopPage, "#o_wsale_products_header");
        updateElementContent(updatedShopPage, "#o_wsale_floating_bar");

        const productGridSelector = ".o_wsale_products_grid_table_wrapper";
        const emptyGridSelector = ".o_wsale_empty_products_grid";
        const isEmptyGrid = updatedShopPage.querySelector(emptyGridSelector);
        const wasEmptyGrid = document.querySelector(emptyGridSelector);
        const gridSelector = isEmptyGrid ? emptyGridSelector : productGridSelector;
        const currSelector = wasEmptyGrid ? emptyGridSelector : productGridSelector;;
        const adjustClasses = (el) => {
            if (isEmptyGrid) {
                el.classList.add("o_wsale_empty_products_grid", "text-center", "mt128", "mb256");
                el.classList.remove("o_wsale_products_grid_table_wrapper");
            } else {
                el.classList.add("o_wsale_products_grid_table_wrapper");
                el.classList.remove("o_wsale_empty_products_grid", "text-center", "mt128", "mb256");
            }
        };
        updateElementContent(
            updatedShopPage,
            gridSelector,
            { postUpdate: adjustClasses, currSelector },
        );

        updateElementContent(updatedShopPage, ".products_pager");
        updateElementContent(
            updatedShopPage,
            ".o_website_offcanvas",
            { postUpdate: (el) => restoreExpandedAccordions(el, expandedTargets) },
        );

        const applyBtn = document.querySelector('#o_wsale_offcanvas_product_count');
        if (applyBtn) {
            setElementContent(applyBtn, data.product_count)
        }
        history.pushState({}, '', targetUrl);
        interaction.services['public.interactions'].startInteractions(shopPageEl);
        productGridWrapper?.classList.remove('opacity-50');
    } catch {
        redirect(targetUrl);
    }
}

/**
 * Return the selected attribute values from the given container.
 *
 * @param {Element} container the container to look into
 */
function getSelectedAttributeValues(container) {
    return Array.from(container.querySelectorAll(
        'input.js_variant_change:checked, select.js_variant_change'
    )).map(el => parseInt(el.value));
}

/**
 * Return a record ID from a slug.
 *
 * @param {string} slug - The slug to parse.
 * @return {undefined|number} - The record ID extracted from the slug, if any.
 */
function unslug(slug) {
    if (!slug) return undefined;
    return parseInt(slug.split('-').at(-1)) || undefined;
}

/**
 * Convert the provided attribute value slugs into search params.
 *
 * @param {string[]} attributeValueSlugs - The attribute value slugs to convert.
 * @return {URLSearchParams} - The search params representing the attribute values.
 */
function getAttributeValueParams(attributeValueSlugs) {
    const attributeValues = new Map();
    for (const slug of attributeValueSlugs) {
        // Group attribute values by attribute.
        const [attribute, attributeValue] = slug.split('/');
        const values = attributeValues.get(attribute) ?? new Set();
        values.add(attributeValue);
        attributeValues.set(attribute, values);
    }
    // Aggregate all attribute values belonging to the same attribute into a single search param.
    return new URLSearchParams(Array.from(attributeValues.entries()).map(
        ([attribute, values]) => [attribute, [...values].join(',')]
    ));
}

/**
 * Filter out any attribute value params from the provided search params.
 *
 * @param {URLSearchParams} searchParams - The search params to filter.
 * @return {URLSearchParams} - The filtered search params.
 */
function clearAttributeValueParams(searchParams) {
    return new URLSearchParams(Array.from(searchParams.entries()).filter(
        ([attribute, _]) => !unslug(attribute)
    ));
}

/**
 * Dispatch a GA4 tracking event to the `.oe_website_sale` element.
 *
 * @param {string} eventName
 * @param {Object} detail
 * @return {void}
 */
function dispatchTrackingEvent(eventName, detail) {
    document.querySelector(".oe_website_sale")?.dispatchEvent(
        new CustomEvent(eventName, { detail })
    );
}

export default {
    updateCartNavBar: updateCartNavBar,
    getSelectedAttributeValues: getSelectedAttributeValues,
    updateQuickReorderSidebar: updateQuickReorderSidebar,
    unslug: unslug,
    getAttributeValueParams: getAttributeValueParams,
    clearAttributeValueParams: clearAttributeValueParams,
    updateShopContent: updateShopContent,
    dispatchTrackingEvent: dispatchTrackingEvent,
};
