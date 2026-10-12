import { registry } from "@web/core/registry";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { kanbanView } from "@web/views/kanban/kanban_view";

export const discussCategoryKanbanView = {
    ...kanbanView,
    Renderer: class DiscussCategoryKanbanRenderer extends KanbanRenderer {
        static template = "mail.DiscussCategoryKanbanRenderer";

        get showNoContentHelper() {
            return (
                !this.props.list.model.root.groups || this.props.list.model.root.groups.length === 0
            );
        }

        /**
         * @override
         * @type {KanbanRenderer["focusNextCard"]}
         */
        focusNextCard(area, direction) {
            const closestCard = document.activeElement.closest(".o_kanban_record");
            if (!closestCard) {
                return;
            }
            const cards = [...area.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")];
            if (!cards.length) {
                return;
            }
            const iCard = cards.indexOf(closestCard);
            const lines = [];
            let lineTop;
            for (const card of cards) {
                if (card.offsetTop !== lineTop) {
                    lineTop = card.offsetTop;
                    lines.push([]);
                }
                lines.at(-1).push(card);
            }
            const iLine = lines.findIndex((line) => line.includes(closestCard));
            const iColumn = lines[iLine].indexOf(closestCard);
            let nextCard;
            switch (direction) {
                case "down":
                case "up": {
                    const line = lines[iLine + (direction === "down" ? 1 : -1)] || [];
                    nextCard = line[Math.min(iColumn, line.length - 1)];
                    break;
                }
                case "right":
                    nextCard = cards[iCard + 1];
                    break;
                case "left":
                    nextCard = cards[iCard - 1];
                    break;
            }
            if (nextCard) {
                nextCard.focus();
                return true;
            }
        }
    },
};

registry.category("views").add("discuss_category_kanban", discussCategoryKanbanView);
