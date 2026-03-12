import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    getSyncAllOrdersContext() {
        const context = super.getSyncAllOrdersContext(...arguments);
        // For SA companies, defer PDF generation to avoid blocking checkout on wkhtmltopdf.
        // ZATCA EDI (clearance/reporting) is still processed synchronously on the server.
        if (this.company.country_id?.code === "SA") {
            context.generate_pdf = false;
        }
        return context;
    },
});
