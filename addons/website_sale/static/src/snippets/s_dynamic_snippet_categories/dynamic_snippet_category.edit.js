import { registry } from '@web/core/registry';
import { omit } from '@web/core/utils/objects';
import { DynamicSnippetCategory } from './dynamic_snippet_category';

// Options read by CSS straight from the dataset, hence kept out of the configuration snapshot: a
// snapshot change restarts the interaction, which empties the grid and refetches it
const CSS_DRIVEN_OPTIONS = ['alignment', 'columns', 'gap', 'rounded', 'size'];

const DynamicSnippetCategoryEdit = (I) =>
    class extends I {
        getConfigurationSnapshot() {
            const snapshot = super.getConfigurationSnapshot();
            if (typeof snapshot !== 'string') {
                return snapshot;
            }
            const { dataset, style } = JSON.parse(snapshot);
            return JSON.stringify({
                dataset: omit(dataset, ...CSS_DRIVEN_OPTIONS),
                style: style,
            });
        }
    };

registry.category('public.interactions.edit').add('website_sale.dynamic_snippet_category', {
    Interaction: DynamicSnippetCategory,
    mixin: DynamicSnippetCategoryEdit,
});
