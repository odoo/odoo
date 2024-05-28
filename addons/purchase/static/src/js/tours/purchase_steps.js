/** @odoo-module **/

class PurchaseAdditionalTourSteps {
    _get_purchase_stock_steps() {
        return [
            {
                auto: true, // Useless final step to trigger congratulation message
                trigger: ".o_purchase_order",
                run: "click",
            },
        ];
    }
}

export default PurchaseAdditionalTourSteps;
