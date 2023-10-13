/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { onExternalClick } from "@mail/utils/common/hooks";
import { ActivityMenu } from "@mail/core/web/activity_menu";
import { useEffect, useRef, useState } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { useCommand } from "@web/core/commands/command_hook";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

const { DateTime } = luxon;

// Add a to-do category for the command palette
registry.category("command_categories").add("to-do", {}, { sequence: 105 });

patch(ActivityMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.state = useState({ addingTodo: false });
        this.todoInputRef = useRef("todoInput");
        this.addingTodoDate = false;
        this.notification = useService("notification");
        useEffect(
            (addingTodo) => {
                if (addingTodo) {
                    this.todoInputRef.el.focus();
                }
            },
            () => [this.state.addingTodo]
        );
        onExternalClick("todoInput", (ev) => {
            if (
                ev.target.closest(".o-mail-ActivityMenu-show") ||
                ev.target.closest(".o_datetime_picker")
            ) {
                return;
            }
            this.state.addingTodo = false;
        });
        useCommand(
            _t("Add a To-Do"),
            () => {
                document.body.click(); // hack to close command palette
                this.createActivityTodo();
            },
            {
                category: "to-do",
                hotkey: "alt+l",
                global: true,
            }
        );
    },

    sortActivityGroups() {
        super.sortActivityGroups();
        this.store.activityGroups.sort((g1, g2) => {
            if (g1.model === "project.task" ? true : false) {
                return -1;
            }
            if (g2.model === "project.task" ? true : false) {
                return 1;
            }
        });
    },

    onKeydownTodoInput(ev) {
        if (ev.key === "Enter") {
            this.saveTodo();
        }
    },

    async createActivityTodo() {
        const wizard = await this.orm.call("mail.activity.todo.create", "create", [{
            "user_id": this.userId,
        }]);
        this.dialogService.add(FormViewDialog, {
            title: "Add a To-Do",
            resModel: "mail.activity.todo.create",
            resId: wizard,
            preventCreate: true,
            size: "md",
        });
    },

    async saveTodo() {
        const urlRegExp = /http(s)?:\/\/(www\.)?[a-zA-Z0-9@:%_+~#=~#?&/=\-;!.]{3,2000}/g;
        const todo = this.todoInputRef.el.value.replace(urlRegExp, '<a href="$&">$&</a>').trim();
        if (!todo) {
            return;
        }
        await this.rpc("/project_todo/new", {
            todo_description: todo,
            date_deadline: this.addingTodoDate ? this.addingTodoDate : DateTime.local(),
        });
        document.body.click(); // hack to close dropdown
        this.notification.add(
            _t("Your to-do has been successfully added to your tasks and scheduled for completion."),
            { type: "success" },
        );
        this.state.addingTodo = false;
    },
});

ActivityMenu.components = {
    ...ActivityMenu.components,
    DateTimeInput,
};
