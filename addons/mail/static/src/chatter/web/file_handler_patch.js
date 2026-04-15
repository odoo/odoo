import { useState } from "@odoo/owl";

import { FileUploader } from "@web/views/fields/file_handler";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

const fileUploaderPatch = {
    setup() {
        super.setup(...arguments);
        if (this.env.services["mail.store"]) {
            this.mailStore = useState(useService("mail.store"));
        }
    },
    async onFileChange() {
        if (!this.env.inChatter || this.env.inComposer) {
            return super.onFileChange(...arguments);
        }
        this.mailStore.isChatterUploading = true;
        try {
            await super.onFileChange(...arguments);
        } finally {
            this.mailStore.isChatterUploading = false;
        }
    },
};
patch(FileUploader.prototype, fileUploaderPatch);
