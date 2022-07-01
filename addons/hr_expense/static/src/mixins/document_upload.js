/** @odoo-module */

import { useService } from '@web/core/utils/hooks';

const { useRef } = owl;

export const ExpenseDocumentUpload = {
    setup() {
        this._super();
        this.actionService = useService('action');
        this.notification = useService('notification');
        this.orm = useService('orm');
        this.http = useService('http');

        this.fileInput = useRef('fileInput');
    },

    uploadDocument() {
        this.fileInput.el.click();
    },

    async onChangeFileInput() {
        const params = {
            csrf_token: odoo.csrf_token,
            ufile: [...this.fileInput.el.files],
            model: 'hr.expense',
            id: 0,
        };

        const fileData = await this.http.post('/web/binary/upload_attachment', params, "text");
        const attachments = JSON.parse(fileData);
        if (attachments.error) {
            throw new Error(attachments.error);
        }
        this.onUpload(attachments);
    },

    async onUpload(attachments) {
        const attachmentIds = attachments.map((a) => a.id);
        if (!attachmentIds.length) {
            this.notification.add(
                this.env._t('An error occurred during the upload')
            );
            return;
        }

        const action = await this.orm.call('hr.expense', 'create_expense_from_attachments', ["", attachmentIds]);
        this.actionService.doAction(action);
    },
};
