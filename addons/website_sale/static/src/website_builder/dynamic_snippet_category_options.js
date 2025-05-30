import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


export class DynamicSnippetCategoryOption extends BaseOptionComponent {
    static template = "website_sale.DynamicSnippetCategoryOptions";

    setup() {
        super.setup();
        this.orm = useService("orm");

        this.state = useState({
            categories: [],
        });

        onWillStart(async () => {
            this.state.categories = await this.orm.call(
                'product.public.category', 'get_snippet_categories', []
            );
        });
    }
}
