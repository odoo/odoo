import { renderToElement } from '@web/core/utils/render';
import { rpc } from '@web/core/network/rpc';

let dataProm;

export function fetchProductSearchData() {
    dataProm ??= rpc('/shop/product_search/filters');
    return dataProm;
}

/**
 * @param {string} key unique identifier of the filter (used to retrieve its selected values)
 * @param {string} label displayed on the dropdown toggle button
 * @param {Array<{id: number, name: string}>} items checkbox choices
 * @param {string} [displayType] 'color' or 'image' to show a swatch preview per item
 */
export function createFilterDropdown(key, label, items, displayType) {
    return renderToElement('website_sale.s_product_search.filter_dropdown', { key, label, items, displayType });
}

/**
 * Renders (or clears) an attribute filter placeholder's content based on its
 * `data-attribute-id`.
 *
 * @param {HTMLElement} filterEl
 * @param {Array<{id: number, name: string, display_type: string, values: Array}>} attributes
 */
export function renderAttributeFilter(filterEl, attributes) {
    filterEl.replaceChildren();
    const attribute = attributes.find((attr) => attr.id === parseInt(filterEl.dataset.attributeId));
    if (attribute) {
        filterEl.appendChild(
            createFilterDropdown(`attribute_${attribute.id}`, attribute.name, attribute.values, attribute.display_type)
        );
    }
}
