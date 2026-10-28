import { _t } from "@web/core/l10n/translation";
import { stepUtils } from "@web_tour/tour_utils";

export const accountTourSteps = {
    draftInvoiceSelector:
        ":has(.o_field_widget[name=move_type] span[raw-value=out_invoice]):has(.o_arrow_button_current[data-value=draft])",
    postedInvoiceSelector:
        ":has(.o_field_widget[name=move_type] span[raw-value=out_invoice]):has(.o_arrow_button_current[data-value=posted])",
    goToAccountMenu(description="Open Invoicing Menu") {
        return stepUtils.goToAppSteps('account.menu_finance', description);
    },
    onboarding() {
        return [];
    },
    newInvoice() {
        return [
            {
                trigger: "button.o_list_button_add",
                content: _t("Now, we'll create your first invoice"),
                run: "click",
            },
        ];
    },
    endSteps() {
        return [{
            trigger: '.breadcrumb-item',
            run: "click",
        }];
    },
}
