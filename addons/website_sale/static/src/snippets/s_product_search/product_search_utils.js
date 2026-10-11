import { rpc } from '@web/core/network/rpc';

/**
 * Fetches the data of the requested filters.
 *
 * @param {Object} [filters] all the filters by default
 * @param {boolean} [filters.tags]
 * @param {boolean} [filters.categories]
 * @param {boolean} [filters.ribbons]
 * @param {boolean|number[]} [filters.attributes] `true` to fetch the names of all the
 *  attributes, or the ids of the attributes to fetch with their values
 */
export function fetchProductSearchData(
    filters = { tags: true, categories: true, ribbons: true, attributes: true },
) {
    return rpc('/shop/product_search/filters', filters, { cache: true });
}

