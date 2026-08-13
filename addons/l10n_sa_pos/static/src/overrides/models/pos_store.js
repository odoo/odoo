import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { renderQRCodeDataURL } from "@l10n_sa_pos/app/utils/qr";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        const company = this.company;
        result.is_simplified =
            (order?.partner_id?.company_type === "person" || !order?.partner_id) &&
            company.country_id?.code === "SA";
        if (order && company?.country_id?.code === "SA") {
            result.is_settlement = order.is_settlement();
            if (!result.is_settlement) {
                const qr_values = order.compute_sa_qr_code(
                    company.name,
                    company.vat,
                    order.date_order,
                    order.get_total_with_tax(),
                    order.get_total_tax()
                );
                result.qr_code = renderQRCodeDataURL(qr_values, 150);
            }
        }
        return result;
    },
});
