import { renderToElement } from '@web/core/utils/render';
import { rpc } from '@web/core/network/rpc';

export const ALL_FILTERS = { tags: true, categories: true, ribbons: true, attributes: true };

/**
 * Fetches the data of the requested filters.
 *
 * @param {Object} filters
 * @param {boolean} [filters.tags]
 * @param {boolean} [filters.categories]
 * @param {boolean} [filters.ribbons]
 * @param {boolean} [filters.attributes] fetch all the attributes
 * @param {number[]} [filters.attribute_ids] fetch only these attributes
 */
export function fetchProductSearchData(filters) {
    return rpc('/shop/product_search/filters', filters, { cache: true });
}

/**
 * Renders (or clears) the dropdown toggle of an attribute filter placeholder
 * based on its `data-attribute-id`.
 *
 * @param {HTMLElement} filterEl
 * @param {Array<{id: number, name: string}>} attributes
 */
export function renderAttributeFilter(filterEl, attributes) {
    filterEl.replaceChildren();
    const attribute = attributes.find((attr) => attr.id === parseInt(filterEl.dataset.attributeId));
    if (attribute) {
        filterEl.appendChild(
            renderToElement('website_sale.s_product_search.filter_dropdown', {
                key: `attribute_${attribute.id}`,
                label: attribute.name,
            })
        );
    }
}
