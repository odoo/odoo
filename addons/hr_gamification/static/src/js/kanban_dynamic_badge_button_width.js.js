/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

patch(KanbanRenderer.prototype, {
    setup() {
        super.setup?.();

        // Delay to ensure DOM is ready
        setTimeout(() => {
            const badge = document.querySelector('.o_kanban_record');
            const button = document.querySelector('.grant_badge_btn');

            if (badge && button) {
                button.style.width = `${badge.offsetWidth}px`;
            }
        }, 0);
    },
});
