import { rpc } from "@web/core/network/rpc";
import { createElementWithContent, setElementContent } from "@web/core/utils/html";
import { redirect } from "@web/core/utils/urls";
import { markup } from "@odoo/owl";

async function updateShopContent(interaction, {
    url,
    searchParams,
}) {
    const targetUrl = `${url.pathname}?${searchParams.toString()}`;

    const productGridWrapper = document.querySelector('.o_wsale_products_grid_table_wrapper');
    productGridWrapper?.classList?.add('opacity-50');

    try {
        const paramsObject = Object.fromEntries(searchParams.entries());
        const data = await interaction.waitFor(rpc('/shop/reload', paramsObject));
        const updatedShopPage = document.createElement('div');
        setElementContent(updatedShopPage, markup(data.html))
        const shopPageEl = document.querySelector('.o_wsale_products_page');
        interaction.services['public.interactions'].stopInteractions(shopPageEl);

        const newSidebar = updatedShopPage.querySelector('#products_grid_before');
        const currentSidebar = document.querySelector('#products_grid_before');
        if (newSidebar && currentSidebar) {
            setElementContent(currentSidebar, markup(newSidebar.innerHTML))
        }

        const newGrid = updatedShopPage.querySelector('.o_wsale_products_grid_table');
        const currentGrid = document.querySelector('.o_wsale_products_grid_table');
        setElementContent(currentGrid, markup(newGrid.innerHTML))

        const newPager = updatedShopPage.querySelector('.products_pager');
        const currentPager = document.querySelector('.products_pager');
        setElementContent(currentPager, markup(newPager.innerHTML))

        const newOffcanvas = updatedShopPage.querySelector('.o_website_offcanvas');
        const currentOffcanvas = document.querySelector('.o_website_offcanvas');
        setElementContent(currentOffcanvas, markup(newOffcanvas.innerHTML))

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
 * Update the cart summary.
 *
 * @param {Object} data
 * @return {void}
 */
function updateCartSummary(data) {
    if (data["website_sale.shorter_cart_summary"]) {
        const shorterCartSummaryEl = document.querySelector(".o_wsale_shorter_cart_summary");
        const newShorterCartSummaryEl = createElementWithContent(
            "div",
            data["website_sale.shorter_cart_summary"]
        );
        shorterCartSummaryEl.replaceWith(...newShorterCartSummaryEl.childNodes);
    }
}

/**
 * Extract text content from edit-mode DOM nodes (mostly labels) to feed OWL cart
 * components (cart lines, totals, quick reorder etc).
 *
 * Values come from server-rendered edit-mode templates and are passed as props
 * to preserve partial editability (e.g. customizable labels).
 *
 * @param {HTMLElement} root - Parent element containing edit-mode DOM
 * @param {Object<string, string>} selectors - Mapping of prop keys to CSS selectors
 * @returns {Object<string, string>} Extracted text values
 */
function extractEditModeText(root, selectors) {
    const data = {};

    for (const key in selectors) {
        const node = root.querySelector(selectors[key]);
        if (node) {
            data[key] = node.textContent;
        }
    }

    return data;
}

export default {
    getSelectedAttributeValues: getSelectedAttributeValues,
    unslug: unslug,
    getAttributeValueParams: getAttributeValueParams,
    clearAttributeValueParams: clearAttributeValueParams,
    updateShopContent: updateShopContent,
    extractEditModeText: extractEditModeText,
    updateCartSummary: updateCartSummary,
};
