/** @odoo-module **/
import { Component } from "@odoo/owl";
import { usePreparationDisplay } from "@pos_preparation_display/app/preparation_display_service";

export class Category extends Component {
    static props = {
        category: Object,
    };

    setup() {
        this.preparationDisplay = usePreparationDisplay();
        this.products = [];
        this.productCount = 0;
    }

    get shouldShowCategory() {
        const category = this.props.category;
        const selectedProducts = this.preparationDisplay.selectedProducts;
        const selectedCategories = this.preparationDisplay.selectedCategories;
        const selectedStageId = this.preparationDisplay.selectedStageId;
        const products = {};

        this.productCount = 0;

        for (const orderline of category.orderlines) {
            if (!orderline.order.displayed) {
                continue;
            }

            if (
                orderline.order.stageId === selectedStageId ||
                !selectedStageId ||
                selectedCategories.has(category.id) ||
                selectedProducts.has(orderline.productId)
            ) {
                let quantity = orderline.productQuantity;
                let cancelled = orderline.productCancelled;

                if (orderline.order.stageId !== selectedStageId && selectedStageId !== 0) {
                    quantity = 0;
                    cancelled = 0;
                }

                if (!products[orderline.productId]) {
                    products[orderline.productId] = {
                        id: orderline.productId,
                        name: orderline.productName,
                        categoryIds: orderline.productCategoryIds,
                        quantity: quantity,
                        cancelled: cancelled,
                    };
                } else {
                    products[orderline.productId].quantity += quantity;
                    products[orderline.productId].cancelled += cancelled;
                }

                this.productCount += quantity - cancelled;
            }
        }

        this.products = Object.values(products).sort((a, b) => b.quantity - a.quantity);
        return this.products.length;
    }
}

Category.template = "pos_preparation_display.Category";
