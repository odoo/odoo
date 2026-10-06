import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { useService } from '@web/core/utils/hooks';

export const AbstractExpenseDocumentUpload = (T) => class AbstractExpenseDocumentUpload extends T {

    setup() {
        super.setup();
        this.actionService = useService('action');
        this.notification = useService('notification');
        this.orm = useService("orm");
        this.http = useService("http");
        this.uiService = useService("ui");
        this.createdExpenseIds = [];
    }

    async generateOpenExpensesAction(currentAction) {
        const actionName = _t("Generate Expenses");
        let domain = [['id', 'in', this.createdExpenseIds]];
        let options = {}
        if (currentAction && currentAction.name === actionName) {
            domain = Domain.or([domain, currentAction.domain]).toList();
            options['stackPosition'] = 'replaceCurrentAction';
        }
        const views = this.uiService.isSmall
            ? [
                [false, "kanban"],
                [false, "list"],
                [false, "form"],
            ]
            : [
                [false, "list"],
                [false, "kanban"],
                [false, "form"],
            ];
        await this.actionService.doAction({
            'name': actionName,
            'res_model': this.modelName,
            'type': 'ir.actions.act_window',
            'views': views,
            'domain': domain,
            'context': this.context,
        }, options);
    }

    async _onChangeFileInput(files) {
        const params = {
            csrf_token: odoo.csrf_token,
            ufile : files,
            model: this.modelName,
            id: 0,
        };

        const attachments = await this.http.post('/web/binary/upload_attachment', params);
        if (attachments.error) {
            throw new Error(attachments.error);
        }
        await this.onUpload(attachments);
    }

    async onUpload(attachments) {
        const attachmentIds = attachments.map((a) => a.id);
        if (!attachmentIds.length) {
            this.notification.add(
                _t('An error occurred during the upload')
            );
            return;
        }

        const createdExpenseIds = await this.orm.call(
            this.modelName,
            'create_expense_from_attachments',
            [attachmentIds, this.viewType],
            { context: this.context },
        );
        this.createdExpenseIds = [...this.createdExpenseIds, ...createdExpenseIds];
    }

    get viewType() {
        return this.uiService.isSmall ? "kanban" : "list";
    }

    get modelName() {
        return "hr.expense";
    }
}
