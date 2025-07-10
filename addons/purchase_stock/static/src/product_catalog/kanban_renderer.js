import { ProductCatalogKanbanRenderer } from "@product/product_catalog/kanban_renderer";
import { useEnv, useState, useEffect } from "@odoo/owl";

export class PurchaseSuggestCatalogKanbanRenderer extends ProductCatalogKanbanRenderer {
    setup() {
        super.setup();
        this.wizard = useState(useEnv().purchaseSuggestWizard);

        useEffect(
            () => {
                console.log(this.wizard);
            },
            () => [
                this.wizard.id,
                this.wizard.basedOn,
                this.wizard.numberOfDays,
                this.wizard.percentFactor,
            ]
        );
    }
}
