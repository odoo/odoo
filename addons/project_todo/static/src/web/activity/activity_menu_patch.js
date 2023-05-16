/** @odoo-module */

import { onExternalClick } from "@mail/utils/hooks";
import { ActivityMenu } from "@mail/web/activity/activity_menu";
import { useEffect, useRef, useState } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(ActivityMenu.prototype, "todo", {
    setup() {
        this._super(...arguments);
        this.rpc = useService("rpc");
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
    },

    sortActivityGroups() {
        this._super();
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

    async saveTodo() {
        const { DateTime } = luxon;
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
            this.env._t("Your to-do has been successfully added to your tasks and scheduled for completion."),
            { type: "success" },
        );
        this.state.addingTodo = false;
    },
});

ActivityMenu.components = {
    ...ActivityMenu.components,
    DateTimeInput,
};
