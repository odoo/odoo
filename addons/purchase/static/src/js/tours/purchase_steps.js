/** @odoo-module **/

class PurchaseAdditionalTourSteps {
    _get_purchase_stock_steps() {
        return [
            {
                // Useless final step to trigger congratulation message
                isActive: ["auto"],
                trigger: ".o_purchase_order",
                run: "click",
            },
        ];
    }
}

export default PurchaseAdditionalTourSteps;
