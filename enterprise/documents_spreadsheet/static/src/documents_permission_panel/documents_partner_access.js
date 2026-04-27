/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { DocumentsPartnerAccess } from "@documents/components/documents_permission_panel/documents_partner_access";

patch(DocumentsPartnerAccess.prototype, {
    /**
     * @returns {string|null}
     */
    noEditorMessage(partner) {
        const partnerInfo = this.props.accessPartners.find((p) => p.id === partner.id).partner_id;
        if (partnerInfo.partner_share && this.props.access.handler === "spreadsheet") {
            return _t("You can not share spreadsheet in edit mode to non-internal user.");
        } else if (this.props.access.handler === "frozen_spreadsheet") {
            return _t("The frozen spreadsheets are readonly.");
        }
        return super.noEditorMessage(partner);
    },
});
