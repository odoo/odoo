/* @odoo-module */

import { DocumentsPermissionPanel } from "@documents/components/documents_permission_panel/documents_permission_panel";
import { patch } from "@web/core/utils/patch";

patch(DocumentsPermissionPanel.prototype, {
    get warningMessage() {
        return null;
    },
    get partnersRoleIsDirty() {
        return null;
    },
    get partnersAccessExpDateIsDirty() {
        return null;
    },
});
