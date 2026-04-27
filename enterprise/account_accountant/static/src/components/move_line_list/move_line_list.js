import { AttachmentViewMoveLine } from "./attachment_view_move_line";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListController } from "@web/views/list/list_controller";
import { SIZES } from "@web/core/ui/ui_service";
import { useChildSubEnv, useState } from "@odoo/owl";
import { makeActiveField } from "@web/model/relational_model/utils";

export class AccountMoveLineListController extends ListController {
    static template = "account_accountant.MoveLineListView";
    static components = {
        ...ListController.components,
        AttachmentViewMoveLine,
    };
    setup() {
        super.setup();
        /** @type {import("@mail/core/common/store_service").Store} */
        this.store = useState(useService("mail.store"));
        this.ui = useState(useService("ui"));
        this.mailPopoutService = useState(useService("mail.popout"));
        this.attachmentPreviewState = useState({
            displayAttachment:
                localStorage.getItem("account.move_line_pdf_previewer_hidden") !== "false",
            selectedRecord: false,
            thread: null,
        });
        this.popout = useState({ active: false });

        useChildSubEnv({
            setPopout: this.setPopout.bind(this),
        });
    }

    get previewEnabled() {
        return (
            !this.env.searchModel.context.disable_preview &&
            (this.ui.size >= SIZES.XXL || this.mailPopoutService.externalWindow)
        );
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
        };
        return params;
    }

    togglePreview() {
        this.attachmentPreviewState.displayAttachment =
            !this.attachmentPreviewState.displayAttachment;
        localStorage.setItem(
            "account.move_line_pdf_previewer_hidden",
            this.attachmentPreviewState.displayAttachment
        );
    }

    setPopout(value) {
        /**
         * This function will set the popout value to false or true depending on the situation.
         * We set popout to True when clicking on a line that has an attachment and then clicking on the popout button.
         * Once the external page is closed, the popout is set to false again.
         */
        if (this.attachmentPreviewState.thread?.attachmentsInWebClientView.length) {
            this.popout.active = value;
        }
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

export class AccountMoveLineListRenderer extends ListRenderer {
    static props = [...ListRenderer.props, "setSelectedRecord?"];
    onCellClicked(record, column, ev) {
        this.props.setSelectedRecord(record);
        super.onCellClicked(record, column, ev);
    }

    findFocusFutureCell(cell, cellIsInGroupRow, direction) {
        const futureCell = super.findFocusFutureCell(cell, cellIsInGroupRow, direction);
        if (futureCell) {
            const dataPointId = futureCell.closest("tr").dataset.id;
            const record = this.props.list.records.filter((x) => x.id === dataPointId)[0];
            this.props.setSelectedRecord(record);
        }
        return futureCell;
    }
}
export const AccountMoveLineListView = {
    ...listView,
    Renderer: AccountMoveLineListRenderer,
    Controller: AccountMoveLineListController,
};

registry.category("views").add("account_move_line_list", AccountMoveLineListView);
