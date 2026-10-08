import { useListener } from "@odoo/owl";

/**
 * The "Upload or drop an expense receipt" helper shown when there is no expense
 * clicks the upload button of the view.
 *
 * @param {() => HTMLElement | null} rootRef
 */
export function useUploadOnHelperClick(rootRef) {
    useListener(rootRef, "click", (ev) => {
        if (ev.target.closest(".o_view_nocontent_expense_receipt")) {
            const buttons = document.querySelectorAll(".o_control_panel .o_button_upload_expense");
            [...buttons].find((button) => button.offsetParent)?.click();
        }
    });
}
