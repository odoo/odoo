/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { onMounted } from "@odoo/owl";

patch(OrderWidget.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");

        onMounted(() => {
            if (this.props.lines.length > 0 && this.props.lines[0].order_id?.config_id.is_kenyan) {
                for (const line of this.props.lines) {
                    if (line.tax_ids?.length === 0) {
                        line.tax_ids.push(...line.product_id.taxes_id);
                    }
                }
            }
        });
    },

    showUnregisteredProductsWarning(lines) {
        return (
            lines.filter(
                (line) =>
                    line.order_id?.config_id.is_kenyan &&
                    (!line.product_id?.checkEtimsFields() || line.tax_ids?.length === 0)
            ).length > 0
        );
    },

    async openProductView(lines) {
        const product_ids = lines
            .filter((line) => !line.product_id?.checkEtimsFields())
            .map((line) => line.product_id.id);
        const actionData = await this.orm.call(
            "product.product",
            "l10n_ke_action_open_products_view",
            [0, product_ids]
        );
        this.actionService.doAction(actionData, { onClose: () => window.location.reload() });
    },
});
