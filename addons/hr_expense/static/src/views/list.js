import { ExpenseAttachment } from "../components/expense_attachment";
import { ExpenseDashboard } from '../components/expense_dashboard';
import { ExpenseMobileQRCode } from '../mixins/qrcode';
import { ExpenseDocumentUpload, ExpenseDocumentDropZone } from '../mixins/document_upload';

import { registry } from '@web/core/registry';
import { SIZES } from "@web/core/ui/ui_service";
import { useService } from '@web/core/utils/hooks';
import { user } from "@web/core/user";
import { listView } from "@web/views/list/list_view";

import { ListController } from "@web/views/list/list_controller";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useChildSubEnv, useState, onWillStart } from "@odoo/owl";


export class ExpenseListController extends ExpenseDocumentUpload(ListController) {
    static template = `hr_expense.ListView`;

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService('action');

        onWillStart(async () => {
            this.userIsExpenseTeamApprover = await user.hasGroup("hr_expense.group_hr_expense_team_approver");
            this.userIsAccountInvoicing = await user.hasGroup("account.group_account_invoice");
        });
    }

    displaySubmit() {
        const records = this.model.root.selection;
        return records.length && records.every(record => record.data.state === 'draft');
    }

    displayApprove() {
        const records = this.model.root.selection;
        return this.userIsExpenseTeamApprover && records.length && records.every(record => record.data.state === 'submitted');
    }

    displayPost() {
        const records = this.model.root.selection;
        return this.userIsAccountInvoicing && records.length && records.every(record => record.data.state === 'approved');
    }

    async onClick (action) {
        const records = this.model.root.selection;
        const recordIds = records.map((a) => a.resId);
        const model = this.model.config.resModel;
        const context = {};
        if (action === 'action_approve') {
            context['validate_analytic'] = true;
        }
        const res = await this.orm.call(model, action, [recordIds], {context: context});
        if (res) {
            await this.actionService.doAction(res, {
                additionalContext: {
                    dont_redirect_to_payments: 1,
                },
                onClose: async () => {
                    await this.model.root.load();
                    this.render(true);
                }
            });
        }
        await this.model.root.load();
    }
}

export class ExpenseListRenderer extends ExpenseDocumentDropZone(ExpenseMobileQRCode(ListRenderer)) {
    static template = "hr_expense.ListRenderer";
}

export const ExpenseListView = {
    ...listView,
    buttonTemplate: 'hr_expense.ListButtons',
    Renderer: ExpenseListRenderer,
    Controller: ExpenseListController,
};

export class ExpenseOverviewListController extends ExpenseListController {
    static template = "hr_expense.OverviewListView";
    static components = { ...ExpenseListController.components, ExpenseAttachment };
    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.mailPopoutService = useService("mail.popout");
        this.attachmentPreviewState = useState({
            displayAttachment: localStorage.getItem(this.previewerStorageKey) !== "false",
            focusedRecord: false,
            thread: null,
        });

        this.popout = useState({ active: false });

        useChildSubEnv({
            setPopout: this.setPopout.bind(this),
        });
    }

    get previewerStorageKey() {
        return "hr_expense.expense_previewer_hidden";
    }

    previewEnabled() {
        return (
            !this.env.searchModel.context.disable_preview &&
            (this.ui.size >= SIZES.XXL || this.mailPopoutService.externalWindow)
        );
    }

    togglePreview() {
        this.attachmentPreviewState.displayAttachment = !this.attachmentPreviewState.displayAttachment;
        localStorage.setItem(
            this.previewerStorageKey,
            this.attachmentPreviewState.displayAttachment
        );
    }

    setPopout(value) {
        if (this.attachmentPreviewState.thread?.attachmentsInWebClientView.length) {
            this.popout.active = value;
        }
    }

    async setThread(lineData) {
        const attachmentField = "attachment_ids"
        const attachments = lineData?.data[attachmentField]?.records || [];
        if (!lineData || !attachments.length) {
            this.attachmentPreviewState.thread = null;
            return;
        }
        const thread = this.store.Thread.insert({
            attachments: attachments.map((attachment) => ({
                id: attachment.resId,
                mimetype: attachment.data.mimetype,
            })),
            id: lineData.resId,
            model: lineData.resModel,
        });
        if (!thread.mainAttachment && thread.attachmentsInWebClientView.length > 0){
            thread.update({mainAttachment: thread.attachmentsInWebClientView[0]});
        }
        this.attachmentPreviewState.thread = thread;
    }

    async setFocusedRecord(ExpenseData) {
        this.attachmentPreviewState.focusedRecord = ExpenseData;
        await this.setThread(ExpenseData, "attachment_ids", "id");
    }
}


export class ExpenseOverviewListRenderer extends ExpenseListRenderer {
    static components = { ...ExpenseListRenderer.components, ExpenseDashboard, ExpenseAttachment };
    static template = "hr_expense.OverviewListRenderer";
    static props = [
        ...ExpenseListRenderer.props,
        "attachmentPreviewState",
        "previewEnabled",
        "popout",
        "setFocusedRecord",
        "togglePreview",
    ];

    findFocusFutureCell(cell, cellIsInGroupRow, direction) {
        const futureCell = super.findFocusFutureCell(cell, cellIsInGroupRow, direction);
        if (futureCell) {
            const dataPointId = futureCell.closest("tr").dataset.id;
            const record = this.props.list.records.filter((x) => x.id === dataPointId)[0];
            this.props.setFocusedRecord(record);
        }
        return futureCell;
    }

    toggleRecordSelection(record) {
        super.toggleRecordSelection(record);
        if (record){this.props.setFocusedRecord(record);}
    }
}

export const ExpenseOverviewListView = {
    ...listView,
    buttonTemplate: 'hr_expense.ListButtons',
    Renderer: ExpenseOverviewListRenderer,
    Controller: ExpenseOverviewListController,
};

registry.category('views').add('hr_expense_tree', ExpenseListView);

registry.category('views').add('hr_expense_overview_tree', ExpenseOverviewListView);
