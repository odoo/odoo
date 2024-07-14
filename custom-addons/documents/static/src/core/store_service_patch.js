/** @odoo-module */

import { Store } from "@mail/core/common/store_service";

import { patch } from "@web/core/utils/patch";

let self;
patch(Store.prototype, {
    hasDocumentsUserGroup: false,
    Document: {
        /** @type {Object.<number, import("@documents/core/document_model").Document>} */
        records: {},
        /**
         * @param {Object} data
         * @returns {import("@documents/core/document_model").Document}
         */
        insert: (data) => self.env.services["document.document"].insert(data),
    },
    setup() {
        super.setup();
        self = this;
    },
});
