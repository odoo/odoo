import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

class AppointmentShareLinkListController extends ListController {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    async onClickCreate() {
        this.dialog.add(FormViewDialog, {
            resModel: "appointment.invite",
            size: "md",
            title: _t("Create a Share Link"),
        });
    }

    async openRecord(record) {
        this.dialog.add(FormViewDialog, {
            resId: record.resId,
            resModel: "appointment.invite",
            size: "md",
            title: _t("Update a Share Link"),
        });
    }
}

registry.category("views").add("appointment_share_link_list", {
    ...listView,
    Controller: AppointmentShareLinkListController,
});
