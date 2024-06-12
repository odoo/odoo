/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ActivityMenu } from "@mail/core/web/activity_menu";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { useCommand } from "@web/core/commands/command_hook";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

// Add a to-do category for the command palette
registry.category("command_categories").add("to-do", {}, { sequence: 105 });

patch(ActivityMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        useCommand(
            _t("Add a To-Do"),
            () => {
                document.body.click(); // hack to close command palette
                this.createActivityTodo();
            },
            {
                category: "to-do",
                hotkey: "alt+shift+t",
                global: true,
            }
        );
    },

    async createActivityTodo() {
        const wizard = await this.orm.call("mail.activity.todo.create", "create", [{
            "user_id": this.userId,
        }]);
        this.dialogService.add(FormViewDialog, {
            title: _t("Add a To-Do"),
            resModel: "mail.activity.todo.create",
            resId: wizard,
            preventCreate: true,
            size: "md",
        });
    },
});
