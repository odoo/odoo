import { registry } from '@web/core/registry';
import { ProductSearchSnippet } from './product_search_snippet';

const ProductSearchSnippetEdit = (I) => class extends I {
    // Keep the filters of the unavailable attributes visible, so that they can be removed
    hideUnavailableFilter() {}

    onClickSearch() {}
};

registry
    .category('public.interactions.edit')
    .add('website_sale.product_search_snippet', {
        Interaction: ProductSearchSnippet,
        mixin: ProductSearchSnippetEdit,
    });
