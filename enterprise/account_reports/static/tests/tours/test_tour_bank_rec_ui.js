import { patch } from "@web/core/utils/patch";
import { accountTourSteps } from "@account/js/tours/account";

patch(accountTourSteps, {
    bankRecUiReportSteps() {
        return [
            {
                trigger: ".o_bank_rec_selected_st_line:contains('line1')",
            },
            {
                content: "balance is 2100",
                trigger: ".btn-link:contains('$ 2,100.00')",
                run: "click",
            },
            {
                trigger: "span:contains('General Ledger')",
            },
            {
                content: "Breadcrumb back to Bank Reconciliation from the report",
                trigger: ".breadcrumb-item a:contains('Bank Reconciliation')",
                run: "click",
            },
        ];
    },
});
