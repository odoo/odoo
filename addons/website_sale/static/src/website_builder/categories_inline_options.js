import { BaseOptionComponent, useDomState } from '@html_builder/core/utils';
import { onWillStart, useState } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';
import { isMobileView } from "@html_builder/utils/utils";


export class CategoriesInlineOption extends BaseOptionComponent {
    static template = 'website_sale.CategoriesInlineOption';

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.website = useService('website');
        const domState = useDomState((editingElement) => ({
            filterId: editingElement.dataset.filterId,
        }));
        this.state = useDomState((editingElement) => ({
            showParentOpt: false,
            isMobileView: isMobileView(editingElement),
        }));

        onWillStart(async () => {
            this.dynamicOptionParams = {
                dynamicFilters: await this.orm.call(
                    'product.public.category',
                    'get_snippet_categories',
                    [this.website.currentWebsiteId],
                ),
                domState: domState,
                getFilteredTemplates: () => [],
                showFilterOption: () => false,
            };
        });
    }
}
