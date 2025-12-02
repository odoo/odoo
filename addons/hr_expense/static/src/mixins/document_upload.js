import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { useBus, useRefListener, useService } from '@web/core/utils/hooks';
import { onWillStart, useRef, useEffect, useState } from "@odoo/owl";

export const ExpenseDocumentDropZone = (T) => class ExpenseDocumentDropZone extends T {
    static props = [
        ...T.props,
        'uploadDocument',
    ];

    setup() {
        super.setup();
        this.dragState = useState({
            showDragZone: false,
        });
        this.root = useRef("root");

        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                const highlight = this.highlight.bind(this);
                const unhighlight = this.unhighlight.bind(this);
                const drop = this.onDrop.bind(this);
                el.addEventListener("dragover", highlight);
                el.addEventListener("dragleave", unhighlight);
                el.addEventListener("drop", drop);
                return () => {
                    el.removeEventListener("dragover", highlight);
                    el.removeEventListener("dragleave", unhighlight);
                    el.removeEventListener("drop", drop);
                };
            },
            () => [document.querySelector('.o_content')]
        );

        useRefListener(this.root, 'click', (ev) => {
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

export const ExpenseDocumentUpload = (T) => class ExpenseDocumentUpload extends T {
    setup() {
        super.setup();
        this.actionService = useService('action');
        this.notification = useService('notification');
        this.orm = useService('orm');
        this.http = useService('http');
        this.shareTarget = useService("shareTarget");
        this.fileInput = useRef('fileInput');
        this.root = useRef("root");

        this.uploadsProcessing = 0;
        this.createdExpenseIds = [];

        useBus(this.env.bus, "change_file_input", async (ev) => {
            this.fileInput.el.files = ev.detail.files;
            this.uploadsProcessing++;
            await this.onChangeFileInput();
        });

        onWillStart(async () => {
            if (this.shareTarget.hasSharedFiles()) {
                const files = this.shareTarget.getSharedFilesToUpload();
                await this._onChangeFileInput(files);
            }
        });
    }

    uploadDocument() {
        this.uploadsProcessing++;
        this.fileInput.el.click();
    }

    async onChangeFileInput() {
        try {
            await this._onChangeFileInput([...this.fileInput.el.files]);
            if (this.uploadsProcessing === 1) {
                const actionName = _t("Generate Expenses");
                const currentAction = this.actionService.currentController.action;
                let domain = [['id', 'in', this.createdExpenseIds]];
                let options = {}
                if (currentAction.name === actionName) {
                    domain = Domain.or([domain, currentAction.domain]).toList();
                    options['stackPosition'] = 'replaceCurrentAction';
                }
                await this.actionService.doAction({
                    'name': actionName,
                    'res_model': 'hr.expense',
                    'type': 'ir.actions.act_window',
                    'views': [[false, this.env.config.viewType], [false, 'form']],
                    'domain': domain,
                    'context': this.props.context,
                }, options);
            }
        } finally {
            this.uploadsProcessing--;
        }
    }

    async _onChangeFileInput(files) {
        const params = {
            csrf_token: odoo.csrf_token,
            ufile : files,
            model: 'hr.expense',
            id: 0,
        };

        const fileData = await this.http.post('/web/binary/upload_attachment', params, "text");
        const attachments = JSON.parse(fileData);
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
            'hr.expense',
            'create_expense_from_attachments',
            [attachmentIds, this.env.config.viewType],
            { context: this.props.context },
        );
        this.createdExpenseIds = [...this.createdExpenseIds, ...createdExpenseIds];
    }
};
