/** @odoo-module **/

import { AttachmentView } from "@mail/core/common/attachment_view";

import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListController } from "@web/views/list/list_controller";
import { SIZES } from '@web/core/ui/ui_service';
import { useState } from "@odoo/owl";
import { makeActiveField } from "@web/model/relational_model/utils";

export class AccountMoveLineListController extends ListController {
    setup() {
        super.setup();
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = useState(useService("mail.store"));
        this.ui = useService("ui");
        this.attachmentPreviewState = useState({
            previewEnabled: !this.env.searchModel.context.disable_preview && this.ui.size >= SIZES.XXL,
            displayAttachment: localStorage.getItem('account.move_line_pdf_previewer_hidden') !== 'false',
            selectedRecord: false,
            thread: null,
        });
        useBus(this.ui.bus, "resize", this.evaluatePreviewEnabled);
    }

    get modelParams() {
        const params = super.modelParams;
        params.config.activeFields.move_attachment_ids = makeActiveField();
        params.config.activeFields.move_attachment_ids.related = {
            fields: {
                mimetype: { name: "mimetype", type: "char" },
            },
            activeFields: {
                mimetype: makeActiveField(),
            },
        }
        return params;
    }

    togglePreview() {
        this.attachmentPreviewState.displayAttachment = !this.attachmentPreviewState.displayAttachment;
        localStorage.setItem('account.move_line_pdf_previewer_hidden', this.attachmentPreviewState.displayAttachment);
    }

    evaluatePreviewEnabled() {
        this.attachmentPreviewState.previewEnabled = !this.env.searchModel.context.disable_preview && this.ui.size >= SIZES.XXL;
    }

    setSelectedRecord(accountMoveLineData) {
        this.attachmentPreviewState.selectedRecord = accountMoveLineData;
        this.setThread(this.attachmentPreviewState.selectedRecord);
    }

    async setThread(accountMoveLineData) {
        if (!accountMoveLineData || !accountMoveLineData.data.move_attachment_ids.records.length) {
            this.attachmentPreviewState.thread = null;
            return;
        }
        const thread = this.store.Thread.insert({
            attachments: accountMoveLineData.data.move_attachment_ids.records.map((attachment) => ({
                id: attachment.resId,
                mimetype: attachment.data.mimetype,
            })),
            id: accountMoveLineData.data.move_id[0],
            model: accountMoveLineData.fields["move_id"].relation,
        });
        if (!thread.mainAttachment && thread.attachmentsInWebClientView.length > 0) {
            thread.update({ mainAttachment: thread.attachmentsInWebClientView[0] });
        }
        this.attachmentPreviewState.thread = thread;
    }
}
AccountMoveLineListController.template = 'account_accountant.MoveLineListView';
AccountMoveLineListController.components = {
    ...ListController.components,
    AttachmentView,
};

export class AccountMoveLineListRenderer extends ListRenderer {
    onCellClicked(record, column, ev) {
        this.props.setSelectedRecord(record);
        super.onCellClicked(record, column, ev);
    }

    findFocusFutureCell(cell, cellIsInGroupRow, direction) {
        const futureCell = super.findFocusFutureCell(cell, cellIsInGroupRow, direction);
        if (futureCell) {
            const dataPointId = futureCell.closest('tr').dataset.id;
            const record = this.props.list.records.filter(x=>x.id === dataPointId)[0];
            this.props.setSelectedRecord(record);
        }
        return futureCell;
    }
}
AccountMoveLineListRenderer.props = [...ListRenderer.props, "setSelectedRecord?"];
export const AccountMoveLineListView = {
    ...listView,
    Renderer: AccountMoveLineListRenderer,
    Controller: AccountMoveLineListController,
};

registry.category("views").add('account_move_line_list', AccountMoveLineListView);
