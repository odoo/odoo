import { onWillStart } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CheckoutPageOption extends BaseOptionComponent {
    static id = "checkout_page_option";
    static template = "website_sale.CheckoutPageOption";
    static dependencies = ["checkoutPageOption"];

    setup() {
        super.setup();
        const websiteService = useService("website");
        const websiteId = websiteService.currentWebsite.id;
        this.domain = [
            "|",
            ["website_id", "=", false],
            ["website_id", "=", websiteId],
        ];
        const { loadSelectedCategories } = this.dependencies.checkoutPageOption;
        onWillStart(async () => {
            const selection = await loadSelectedCategories();
            if (selection.length) {
                const editingElement = this.env.getEditingElement();
                editingElement.dataset.extraStepCategoryIds =
                    JSON.stringify(selection);
            }
        });
    }
}

registry.category("website-options").add(CheckoutPageOption.id, CheckoutPageOption);
