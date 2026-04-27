/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { DocumentsAccessSettings } from "@documents/components/documents_permission_panel/documents_access_settings";

patch(DocumentsAccessSettings.prototype, {
    get errorAccessLinkEdit() {
        if (this.props.access.handler === "frozen_spreadsheet") {
            return _t("The frozen spreadsheets are readonly.");
        } else if (this.props.access.handler === "spreadsheet") {
            return _t(
                "The spreadsheets can not be shared in edit mode with a link, change Internal to give write access."
            );
        }
        return super.errorAccessLinkEdit;
    },

    get errorAccessInternalEdit() {
        if (this.props.access.handler === "frozen_spreadsheet") {
            return _t("The frozen spreadsheets are readonly.");
        }
        return super.errorAccessInternalEdit;
    },
});
