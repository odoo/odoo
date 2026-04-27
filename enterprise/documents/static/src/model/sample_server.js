/* @odoo-module */

import { SampleServer } from "@web/model/sample_server";
import { patch } from "@web/core/utils/patch";

/**
 * Document uses a special option to make the browser generates the thumbnail of PDFs
 * and then save it on the record. This prevents the browser from generating the
 * thumbnail of the sample data.
 */
patch(SampleServer.prototype, {
    _getRandomSelectionValue(modelName, field) {
        if (modelName === "documents.document" && field.name === "thumbnail_status") {
            return false;
        }
        return super._getRandomSelectionValue(...arguments);
    },
});
