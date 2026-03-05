import {KanbanController} from "@web/views/kanban/kanban_controller";

export class DocumentPageKanbanController extends KanbanController {
    /**
     * @param {Object} record
     */
    async openRecord(record) {
        // eslint-disable-next-line no-undef
        const element = document.querySelector(
            `.o_kanban_record[data-id="${record.id}"] .o_document_page_kanban_boxes a`
        );

        if (this.props.resModel === "document.page" && element) {
            element.click();
        } else {
            await super.openRecord(record);
        }
    }
}
