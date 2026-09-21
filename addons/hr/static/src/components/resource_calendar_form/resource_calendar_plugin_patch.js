import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { ResourceCalendarPlugin } from "@resource/plugins/resource_calendar_plugin";

patch(ResourceCalendarPlugin.prototype, {
    async confirmAttendanceChanges() {
        // A variable schedule writes its attendances right away, so the form is never saved.
        const employeesCount = this.record?.data.employees_count || 0;
        if (employeesCount > 1) {
            const confirmed = await new Promise((resolve) => {
                // Same warning as the one raised when a shared schedule form is saved.
                this.env.services.dialog.add(ConfirmationDialog, {
                    title: _t("Confirmation Warning"),
                    body: _t(
                        "This working schedule is used by %s employee(s), are you sure you want change it for all employees?",
                        employeesCount
                    ),
                    confirmLabel: _t("Confirm"),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                });
            });
            if (!confirmed) {
                return false;
            }
        }
        return super.confirmAttendanceChanges();
    },
});
