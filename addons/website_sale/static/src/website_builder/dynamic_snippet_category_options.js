import { useDomState } from '@html_builder/core/utils';
import { onWillStart } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';
import { DynamicSnippetOption } from '@website/builder/plugins/options/dynamic_snippet_option';
import { registry } from '@web/core/registry';
import {
    dynamicContentOfDynamicSnippet,
    getSharedSnippetArg,
} from '@website/builder/plugins/options/dynamic_snippet_option_plugin';

export class DynamicSnippetCategoryOption extends DynamicSnippetOption {
    static id = 'dynamic_snippet_category_option';
    static template = 'website_sale.DynamicSnippetCategoryOptions';

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.website = useService('website');
        this.dynamicOptionParams.domState = useDomState((editingElement) => {
            const dynamicEl = dynamicContentOfDynamicSnippet(editingElement);
            return {
                parentCategoryId: getSharedSnippetArg(dynamicEl, "content_data").parent_category_id,
            };
        });
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

registry.category("website-options").add(DynamicSnippetCategoryOption.id, DynamicSnippetCategoryOption);
