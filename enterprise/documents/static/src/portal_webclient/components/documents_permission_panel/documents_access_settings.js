/* @odoo-module */

import { DocumentsAccessSettings } from "@documents/components/documents_permission_panel/documents_access_settings";
import { patch } from "@web/core/utils/patch";

patch(DocumentsAccessSettings.prototype, {
    errorAccessInternalEdit: {},
    internalAdditionalLabel: {},
});
