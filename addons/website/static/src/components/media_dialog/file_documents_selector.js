/** This patch is no longer needed, and will be removed in master */

import { patch } from "@web/core/utils/patch";
import { FileDocumentsSelector } from "@html_editor/main/media/media_dialog/file_documents_selector";

patch(FileDocumentsSelector.prototype, {
    get attachmentsDomain() {
        const domain = super.attachmentsDomain;
        domain.push("|", ["url", "=", false], "!", ["url", "=like", "/web/image/website.%"]);
        domain.push(["key", "=", false]);
        return domain;
    },
});
