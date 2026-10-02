import { registry } from '@web/core/registry';
import { _t } from '@web/core/l10n/translation';
import { ProductSearchSnippet } from './product_search_snippet';

const ProductSearchSnippetEdit = (I) => class extends I {
    start() {
        super.start();
        // Keep the filters of the unavailable attributes visible, so that they can be removed
        for (const filterEl of this.el.querySelectorAll('.s_product_search_attribute_filter:empty')) {
            this.renderAt('website_sale.s_product_search.filter_dropdown', {
                key: `attribute_${filterEl.dataset.attributeId}`,
                label: _t('Unavailable attribute'),
                items: [],
            }, filterEl);
        }
    }

    getConfigurationSnapshot() {
        const snapshot = JSON.parse(super.getConfigurationSnapshot() || '{}');
        snapshot.attributeIds = this.getAttributeIds();
        return JSON.stringify(snapshot);
    }

    isImpactedBy(el) {
        // Re-render the dropdowns when an attribute filter is added or changed
        return this.el.contains(el);
    }

    onClickSearch() {}
};

registry
    .category('public.interactions.edit')
    .add('website_sale.product_search_snippet', {
        Interaction: ProductSearchSnippet,
        mixin: ProductSearchSnippetEdit,
    });
