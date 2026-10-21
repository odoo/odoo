import { PosStore } from "@point_of_sale/app/services/pos_store";
import { DailySalesReportPopup } from "@pos_hr/app/components/popups/daily_sales_report_popup/daily_sales_report_popup";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";

async function printSaleDetailsWithEmployees(pos) {
    const includeEmployees = await makeAwaitable(pos.dialog, DailySalesReportPopup, {});
    if (includeEmployees === undefined) {
        return;
    }

    const employeesSaleDetailsPromise = includeEmployees
        ? pos.data.call("pos.session", "get_employees_sale_details", [[pos.session.id]])
        : [];
    const result = await pos.ticketPrinter.printSaleDetailsReceipt();
    const employeesSaleDetails = await employeesSaleDetailsPromise;
    if (!result?.successful) {
        return;
    }
    for (const saleDetails of employeesSaleDetails) {
        const employeeResult = await pos.ticketPrinter.printSaleDetailsReceipt({ saleDetails });
        if (!employeeResult?.successful) {
            break;
        }
    }
}

patch(PosStore.prototype, {
    async printSaleDetails() {
        if (!this.config.module_pos_hr) {
            return super.printSaleDetails();
        }
        return printSaleDetailsWithEmployees(this);
    },
});
