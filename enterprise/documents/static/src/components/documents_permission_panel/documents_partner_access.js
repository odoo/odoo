/** @odoo-module **/

import { DocumentsAccessExpirationDateBtn } from "./documents_access_expiration_date_btn";
import { DocumentsPermissionSelect } from "./documents_permission_select";
import { DocumentsRemovePartnerButton } from "./documents_remove_partner_button";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { user } from "@web/core/user";
import { Component } from "@odoo/owl";

export class DocumentsPartnerAccess extends Component {
    static components = {
        DocumentsAccessExpirationDateBtn,
        DocumentsPermissionSelect,
        DocumentsRemovePartnerButton,
    };
    static props = {
        access: Object,
        accessPartners: Array,
        basePartnersRole: Object,
        basePartnersAccessExpDate: Object,
        isAdmin: Boolean,
        isInternalUser: Boolean,
        isCurrentUser: Function,
        disabled: Boolean,
        ownerUser: [Object, Boolean],
        onChangePartnerRole: Function,
        removeDocumentAccess: Function,
        selections: Array,
        setExpirationDate: Function,
    };
    static template = "documents.PartnerAccess";

    /**
     * @returns {string|undefined}
     */
    noEditorMessage(partner) {
        return undefined;
    }

    getFormattedLocalExpirationDate(accessPartner) {
        return deserializeDateTime(accessPartner.expiration_date, {
            tz: user.context.tz,
        })
            .setLocale(user.context.lang.replaceAll("_", "-"))
            .toLocaleString(luxon.DateTime.DATETIME_SHORT);
    }
}
