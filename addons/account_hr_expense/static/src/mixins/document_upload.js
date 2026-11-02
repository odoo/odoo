import { proxy, signal, t, useListener, useProps } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from '@web/core/utils/hooks';

export const ExpenseDocumentDropZone = (T, parentProps) => class ExpenseDocumentDropZone extends T {
    props = useProps({
        ...parentProps,
        uploadDocument: t.function(),
    });

    setup() {
        super.setup();
        this.dragState = proxy({
            showDragZone: false,
        });

        // The drop zone is the whole content area the renderer is displayed in.
        const contentEl = () => this.rootRef()?.closest(".o_content");
        useListener(contentEl, "dragover", this.highlight.bind(this));
        useListener(contentEl, "dragleave", this.unhighlight.bind(this));
        useListener(contentEl, "drop", this.onDrop.bind(this));

        useListener(this.rootRef, 'click', (ev) => {
            let targetElement = ev.target;
            if (targetElement.closest('.o_view_nocontent_expense_receipt')) {
                this.props.uploadDocument();
            }
        });
    }

    highlight(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.dragState.showDragZone = true;
    }

    unhighlight(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.dragState.showDragZone = false;
    }

    async onDrop(ev) {
        ev.preventDefault();
        await this.env.bus.trigger("change_file_input", {
            files: ev.dataTransfer.files,
        });        
        this.dragState.showDragZone = false;
    }
};

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

export const ExpenseDocumentUpload = (T) => class ExpenseDocumentUpload extends AbstractExpenseDocumentUpload(T) {
    fileInput = signal.ref();

    setup() {
        super.setup();
        this.uploadsProcessing = 0;

        useBus(this.env.bus, "change_file_input", async (ev) => {
            this.fileInput().files = ev.detail.files;
            this.uploadsProcessing++;
            await this.onChangeFileInput();
        });
    }

    uploadDocument() {
        this.uploadsProcessing++;
        this.fileInput().click();
    }

    async onChangeFileInput() {
        try {
            await this._onChangeFileInput([...this.fileInput().files]);
            if (this.uploadsProcessing === 1) {
                await this.generateOpenExpensesAction(this.actionService.currentController.action);
            }
        } finally {
            this.uploadsProcessing--;
        }
    }

    get viewType() {
        return this.env.config.viewType;
    }

    get context() {
        return this.props.context;
    }
};
