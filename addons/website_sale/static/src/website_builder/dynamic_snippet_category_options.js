import { BaseOptionComponent } from '@html_builder/core/utils';
import { onWillStart } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';
import { ShadowOption } from '@html_builder/plugins/shadow_option';


export class DynamicSnippetCategoryOption extends BaseOptionComponent {
    static template = 'website_sale.DynamicSnippetCategoryOptions';
    static components = {
        ShadowOption,
    };

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.website = useService('website');
        this.categories = [];

        onWillStart(async () => {
            this.categories = await this.orm.call(
                'product.public.category',
                'get_snippet_categories',
                [this.website.currentWebsiteId],
            );
        });
    }
}
