import { useDomState } from '@html_builder/core/utils';
import { onWillStart } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';
import { DynamicSnippetOption } from '@website/builder/plugins/options/dynamic_snippet_option';
import { registry } from '@web/core/registry';

export class DynamicSnippetCategoryOption extends DynamicSnippetOption {
    static id = 'dynamic_snippet_category_option';
    static template = 'website_sale.DynamicSnippetCategoryOptions';

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.website = useService('website');
        this.dynamicOptionParams.domState = useDomState(editingElement => ({
            parentCategoryId: editingElement.dataset.parentCategoryId,
        }))
        this.categories = [];

        onWillStart(async () => {
            this.categories = await this.orm.call(
                'product.public.category',
                'get_available_snippet_categories',
                [this.website.currentWebsiteId],
            );
        });
    }
}

registry.category("builder-options").add(DynamicSnippetCategoryOption.id, DynamicSnippetCategoryOption);
