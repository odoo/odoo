import { KanbanColumnQuickCreate, kanbanColumnQuickCreateProps } from "@web/views/kanban/kanban_column_quick_create";

import { onMounted, t, useProps } from "@odoo/owl";

export class ProjectTaskColumnQuickCreate extends KanbanColumnQuickCreate {
    static template = "project.ProjectTaskColumnQuickCreate";

    props = useProps({
        ...kanbanColumnQuickCreateProps,
        canFold: t.boolean(),
    });

    setup() {
        super.setup();
        onMounted(async () => {
            if (this.props.folded) {
                return;
            }

            await Promise.resolve();
            this.inputRef()?.focus();
        });
    }

    /**
     * @override
     *
     * to prevent folding the column when the user is not allowed to do so,
     * like when no stage exists for the current project
     */
    fold() {
        if (this.props.canFold) {
            super.fold();
        }
    }
}
