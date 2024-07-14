/* @odoo-module */

import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";
import { assignDefined } from "@mail/utils/common/misc";

patch(Attachment.prototype, {
    documentId: null,

    update(data) {
        super.update(data);
        assignDefined(this, data, ["documentId"]);
    },

    get urlRoute() {
        if (this.documentId) {
            return this.isImage
                ? `/web/image/${this.documentId}`
                : `/web/content/${this.documentId}`;
        }
        return super.urlRoute;
    },

    get urlQueryParams() {
        const res = super.urlQueryParams;
        if (this.documentId) {
            res["model"] = "documents.document";
            return res;
        }
        return res;
    },
});
