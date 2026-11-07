import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormControllerWithHTMLExpander } from "@resource/views/form_with_html_expander/form_controller_with_html_expander";
import { formViewWithHtmlExpander } from "@resource/views/form_with_html_expander/form_view_with_html_expander";
import { registry } from "@web/core/registry";

export class SaleProjectProjectFormController extends FormControllerWithHTMLExpander {
    async onWillSaveRecord(record) {
        let linkedProject = false;

        if ("allow_billable" in record._changes && record._changes.allow_billable === false) {
            linkedProject = await record.model.orm.call(
                record.resModel,
                "check_allow_billable_projects",
                [[record.resId]],
            );
        }

        if (linkedProject) {
            const confirmation = await new Promise((resolve) => {
                this.env.services.dialog.add(ConfirmationDialog, {
                    title: _t("Confirmation Required"),
                    body: _t("Making this project non-billable will unlink it from any products that create tasks in it or use it as a template. Are you sure you want to continue?"),
                    confirm: async () => resolve(true),
                    cancel: async () => resolve(false),
                });
            });

            if (!confirmation) {
                record.update({ allow_billable: true });
                return false;
            }
        }

        return super.onWillSaveRecord(...arguments);
    }
}

export const saleProjectProjectFormView = {
    ...formViewWithHtmlExpander,
    Controller: SaleProjectProjectFormController,
};

registry.category("views").add("sale_project_project_form", saleProjectProjectFormView);
