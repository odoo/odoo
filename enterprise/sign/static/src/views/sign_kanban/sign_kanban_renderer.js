/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { SignDocumentDropZone } from '../../mixin/document_upload';
import { SignActionHelper } from '@sign/views/helper/sign_action_helper';

export class SignKanbanRenderer extends SignDocumentDropZone(KanbanRenderer) {
    static template = "sign.KanbanRenderer";
    static components = { 
        ...KanbanRenderer.components,
        SignActionHelper,
    };

    /**
     * @override
     * Prevent moving records for sign request items
     */
    get canMoveRecords() {
        return super.canMoveRecords && this.props.list.resModel !== "sign.request";
    }

    /**
     * @override
     * Prevent moving groups for sign request items
     */
    get canResequenceGroups() {
        return super.canResequenceGroups && this.props.list.resModel !== "sign.request";
    }
}
