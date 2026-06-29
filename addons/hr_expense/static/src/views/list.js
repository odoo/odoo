import { render } from "@web/owl2/utils";
import { ExpenseDashboard } from "@hr_expense/components/expense_dashboard";
import { ExpenseDocumentUpload, ExpenseDocumentDropZone } from "@hr_expense/mixins/document_upload";
import { ExpenseAttachmentPreviewMixin } from "./attachment_preview/expense_attachment_preview";
import { ExpenseAttachmentView } from "./attachment_preview/expense_attachment_view";
import { makeActiveField} from "@web/model/relational_model/utils"

import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { user } from "@web/core/user";
import { listView } from "@web/views/list/list_view";

import { ListController } from "@web/views/list/list_controller";
import { ListRenderer, listRendererProps } from "@web/views/list/list_renderer";
import { onWillStart } from "@odoo/owl";

export class ExpenseListController extends ExpenseDocumentUpload(ExpenseAttachmentPreviewMixin(ListController)) {
    static components = { ...ListController.components, ExpenseAttachmentView };
    get previewStorageKey() {
        return "hr_expense_list.pdf_previewer_hidden";
    }
    get modelParams() {
        const params = super.modelParams;
        params.config.activeFields.attachment_ids = makeActiveField();
        params.config.activeFields.attachment_ids.related = {
            fields: {
                mimetype: { name: "mimetype", type: "char" },
            },
            activeFields: {
                mimetype: makeActiveField(),
            },
        };
        return params;
    }
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

    get actionMenuItems() {
        const menuItems = super.actionMenuItems || {};
        if (menuItems.print) {
            menuItems.print = [];
        }
        return menuItems;
    }

    // 2. Add a direct print function
    async onClickPrint() {
        // Collect IDs from selected records
        const resIds = this.model.root.selection.map(r => r.resId);

        // Execute your custom PDF report action directly
        this.env.services.action.doAction('hr_expense.action_report_hr_expense', {
            additionalContext: { active_ids: resIds },
        });
    }

    async setSelectedRecord(expenseRecord) {
        this.attachmentPreviewState.selectedRecord = expenseRecord;
        const attachments = expenseRecord?.data?.attachment_ids?.records || [];
        if (!expenseRecord || !attachments.length) {
            this.attachmentPreviewState.thread = null;
            return;
        }
        const thread = this.store["mail.thread"].insert({
            attachments: attachments.map((a) => ({
                id: a.resId,
                mimetype: a.data.mimetype,
            })),
            id: expenseRecord.resId,
            model: "hr.expense",
        });
        if (!thread.message_main_attachment_id && thread.attachmentsInWebClientView.length > 0) {
            thread.update({ message_main_attachment_id: thread.attachmentsInWebClientView[0] });
        }
        this.attachmentPreviewState.thread = thread;
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
                    render(this, true);
                }
            });
        }
        await this.model.root.load();
    }
}

export class ExpenseListRenderer extends ExpenseDocumentDropZone(ListRenderer, listRendererProps) {
    static template = "hr_expense.ListRenderer";
    static props = [...ListRenderer.props, "setSelectedRecord", "uploadDocument"];

    async onCellClicked(record, column, ev) {
        this.props.setSelectedRecord(record);
        if (record.selected || column.name === "name") {
            await super.onCellClicked(record, column, ev);
        }
    }

    findFocusFutureCell(cell, cellIsInGroupRow, direction) {
        const futureCell = super.findFocusFutureCell(cell, cellIsInGroupRow, direction);
        if (futureCell) {
            const dataPointId = futureCell.closest("tr").dataset.id;
            const record = this.props.list.records.find((x) => x.id === dataPointId);
            this.props.setSelectedRecord(record);
        }
        return futureCell;
    }
}

export class ExpenseDashboardListRenderer extends ExpenseListRenderer {
    static components = { ...ExpenseDashboardListRenderer.components, ExpenseDashboard };
    static template = "hr_expense.DashboardListRenderer";
}

registry.category('views').add('hr_expense_tree', {
    ...listView,
    buttonTemplate: 'hr_expense.ListButtons',
    Controller: ExpenseListController,
    Renderer: ExpenseListRenderer,
});

registry.category('views').add('hr_expense_dashboard_tree', {
    ...listView,
    buttonTemplate: 'hr_expense.ListButtons',
    Controller: ExpenseListController,
    Renderer: ExpenseDashboardListRenderer,
});
