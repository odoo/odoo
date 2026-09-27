import { ShareTargetItem } from "@web/webclient/share_target/share_target_item";
import { ProjectShareTargetItem } from "@project/webclient/share_target/project_share_target_item";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class TodoProjectShareTargetItem extends ProjectShareTargetItem {
    static name = _t("To-Do");
    static sequence = 6;
    static template = ShareTargetItem.template;

    get defaultState() {
        return {
            ...super.defaultState,
            default_project_id: false,
        };
    }

    async updateProjects() {}

    get context() {
        return {
            ...super.context,
            form_view_ref: "project_todo.project_task_view_todo_form",
        };
    }
}

registry.category("share_target_items").add("todo_project", TodoProjectShareTargetItem);
