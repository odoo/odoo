/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
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

        useBus(this.env.bus, "change_file_input", async (ev) => {
            this.fileInput.el.files = ev.detail.files;
            await this.onChangeFileInput();
        });

        onWillStart(async () => {
            if (this.shareTarget.hasSharedFiles()) {
                const files = this.shareTarget.getSharedFilesToUpload();
                await this._onChangeFileInput(files);
            }
        });
    }

    displayCreateReport() {
        const isExpenseSheet = this.model.config.resModel === "hr.expense.sheet";
        const usesSampleData = this.model.useSampleModel;
        const records = this.model.root.records;
        return !usesSampleData && !isExpenseSheet && records.length && records.some(record => record.data.state === "draft");
    }

    async action_show_expenses_to_submit () {
        const records = this.model.root.selection;
        const res = await this.orm.call(this.model.config.resModel, 'get_expenses_to_submit', [records.map((record) => record.resId)]);
        if (res) {
            await this.actionService.doAction(res, {});
        }
    }

    uploadDocument() {
        this.fileInput.el.click();
    }

    async onChangeFileInput() {
        await this._onChangeFileInput([...this.fileInput.el.files]);
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

        const action = await this.orm.call('hr.expense', 'create_expense_from_attachments', [attachmentIds, this.env.config.viewType]);
        await this.actionService.doAction(action);
    }
};
