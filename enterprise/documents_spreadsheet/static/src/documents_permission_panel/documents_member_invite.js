/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { DocumentsMemberInvite } from "@documents/components/documents_permission_panel/documents_member_invite";

/**
 * Add warning message for non-internal users and load the `partner_share` value.
 */
patch(DocumentsMemberInvite.prototype, {
    _getPartnersSpecification() {
        return { ...super._getPartnersSpecification(), partner_share: 1 };
    },

    _addCreatedPartnersValues(partner) {
        return {
            ...super._addCreatedPartnersValues(partner),
            partner_share: true,
        };
    },

    /**
     * @returns {string|null}
     */
    get noEditorMessage() {
        const partners = this.state.fetchedPartners.filter((p) =>
            this.state.selectedPartners.includes(p.id)
        );
        if (partners.some((p) => p.partner_share) && this.props.access.handler === "spreadsheet") {
            return _t("You can not share spreadsheet in edit mode to non-internal user.");
        } else if (this.props.access.handler === "frozen_spreadsheet") {
            return _t("The frozen spreadsheets are readonly.");
        }
        return super.noEditorMessage;
    },
});
