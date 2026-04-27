/** @odoo-module **/

import { CopyButton } from "@web/core/copy_button/copy_button";
import { Dialog } from "@web/core/dialog/dialog";
import { DocumentsAccessSettings } from "./documents_access_settings";
import { DocumentsMemberInvite } from "./documents_member_invite";
import { DocumentsPartnerAccess } from "./documents_partner_access";
import { serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import { rpcBus } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { Component, onWillStart, useState } from "@odoo/owl";

export class DocumentsPermissionPanel extends Component {
    static components = {
        CopyButton,
        Dialog,
        DocumentsAccessSettings,
        DocumentsMemberInvite,
        DocumentsPartnerAccess,
    };
    static props = {
        document: {
            type: Object,
            shape: {
                id: Number,
                name: { type: String, optional: true },
            },
        },
        close: Function,
        onChangesSaved: { type: Function, optional: true },
    };
    static template = "documents.PermissionPanel";

    setup() {
        this.actionService = useService("action");
        this.basePartnersRole = {};
        this.createdPartners = { choices: [], values: [] };
        this.dialog = useService("dialog");
        this.isAdmin = user.isAdmin;
        this.orm = useService("orm");
        this.documentService = useService("document.document");
        this.isInternalUser = this.documentService.userIsInternal;
        this.state = useState({
            loading: true,
            mainPage: true,
            didSave: false,
        });

        useBus(rpcBus, "RPC:RESPONSE", this.responseCall);

        onWillStart(async () => {
            this.state.loading = true;
            await this.loadMainPage();
            this.state.loading = false;
        });
    }

    get panelTitle() {
        return _t("Share: %(documentName)s", { documentName: this.state.access.display_name });
    }

    get pendingSave() {
        return (
            Object.entries(this.baseAccess).some(
                ([fieldName, value]) => this.state.access[fieldName] !== value
            ) ||
            this.partnersRoleIsDirty ||
            this.partnersAccessExpDateIsDirty
        );
    }

    get copyText() {
        return this.pendingSave ? _t("Save or discard changes first") : _t("Copy Link");
    }

    /**
     * Check whether there is an alert message to display, and which one
     *
     * @returns {string|null}
     */
    get warningMessage() {
        if (
            this.state.access.access_via_link === "edit" &&
            (this.state.access.access_internal === "view" ||
                this.state.access.access_ids.some((a) => a.role === "view"))
        ) {
            const documentType =
                this.state.access.type === "folder" ? _t("folder") : _t("document");
            return _t(
                "All users with access to this %(documentType)s or its parent will have edit permissions.",
                { documentType }
            );
        }
        return null;
    }

    get partnersRoleIsDirty() {
        return this.state.access.access_ids.some((a) => a.role !== this.basePartnersRole[a.id]);
    }

    get partnersAccessExpDateIsDirty() {
        return this.state.access.access_ids.some(
            (a) => a.expiration_date !== this.basePartnersAccessExpDate[a.id]
        );
    }

    revertChanges() {
        Object.assign(this.state.access, this.baseAccess);
        for (const [id, role] of Object.entries(this.basePartnersRole)) {
            const accessPartner = this.state.access.access_ids.find((a) => a.id === parseInt(id));
            accessPartner.role = role;
            accessPartner.expiration_date = this.basePartnersAccessExpDate[id];
        }
    }

    showMainPage(value = true) {
        this.state.mainPage = value;
    }

    async save() {
        this.state.loading = true;
        const userPermission = await this.updateAccessRights();
        if (userPermission === "none") {
            // Don't crash when current user just removed their own access
            await this.actionService.restore(this.actionService.currentController.jsId);
            return;
        }
        await this.loadMainPage();
        this.state.loading = false;
    }

    async loadMainPage() {
        const permissionsData = await this.orm.call("documents.document", "permission_panel_data", [
            this.props.document.id,
        ]);
        this.state.access = permissionsData.record;
        this.state.selections = permissionsData.selections;
        this.selectedPartnersRole = this.state.selections.doc_access_roles
            ? this.state.selections.doc_access_roles[0][0]
            : "";
        this.baseAccess = Object.fromEntries(
            ["access_internal", "access_via_link", "is_access_via_link_hidden"].map((fieldName) => [
                fieldName,
                this.state.access[fieldName],
            ])
        );
        this.basePartnersRole = {};
        (this.state.access.access_ids || []).forEach((a) => (this.basePartnersRole[a.id] = a.role));
        this.basePartnersAccessExpDate = {};
        (this.state.access.access_ids || []).forEach(
            (a) => (this.basePartnersAccessExpDate[a.id] = a.expiration_date)
        );
    }

    /**
     * Create/Update/Unlink access to document/folder.
     * @param {Object} partners Partners to be added.
     * @param {Boolean} notify Whether to notify the `partners`
     * @param {String} message Optional customized message
     */
    async updateAccessRights(partners= undefined, notify = false, message = "") {
        const accessValuesToSend = Object.fromEntries(
            Object.entries(this.baseAccess).map(([field, oldValue]) => [
                field,
                oldValue !== this.state.access[field] ? this.state.access[field] : null,
            ])
        );
        let partnersToUpdate = partners;
        if (this.partnersRoleIsDirty || this.partnersAccessExpDateIsDirty) {
            partnersToUpdate = partnersToUpdate || {};
            this.state.access.access_ids.forEach((a) => {
                const roleUpdated = a.role !== this.basePartnersRole[a.id];
                const expirationUpdated =
                    a.expiration_date !== this.basePartnersAccessExpDate[a.id];
                if (roleUpdated || expirationUpdated) {
                    partnersToUpdate[a.partner_id.id] = [
                        a.role,
                        expirationUpdated ? a.expiration_date : null,
                    ];
                }
            });
        }
        const userPermission = (await this.orm.call("documents.document", "action_update_access_rights", [
            [this.props.document.id],
            accessValuesToSend.access_internal,
            accessValuesToSend.access_via_link,
            accessValuesToSend.is_access_via_link_hidden,
            partnersToUpdate,
            notify,
            message,
        ]))[0];
        this.state.didSave = true;
        return userPermission;
    }

    /**
     * Unset partner access to a document/folder
     * @param {Proxy} accessPartner
     */
    removeDocumentAccess(accessPartner) {
        accessPartner.role = false;
        this.state.partnersRoleIsDirty = true;
    }

    /**
     * @param {Proxy} accessPartner
     * @returns {Boolean}
     */
    isCurrentUser(accessPartner) {
        return accessPartner.partner_id.id === user.partnerId;
    }

    close() {
        if (this.state.didSave) {
            this.props.onChangesSaved?.();
        }
        this.props.close();
    }

    onDiscard() {
        return this.pendingSave ? this.revertChanges() : this.close();
    }

    onShare() {
        return this.pendingSave && this.state.access.user_permission === "edit"
            ? this.save()
            : this.close();
    }

    /**
     * @param {Event} event
     */
    onChangeDocumentAccessInternal(event) {
        this.state.access.access_internal = event.target.selectedOptions[0].value;
    }

    /**
     * @param {Event} event
     */
    onChangeDocumentAccessLink(event) {
        this.state.access.access_via_link = event.target.selectedOptions[0].value;
    }

    onChangeDocumentIsAccessLinkHidden(event) {
        this.state.access.is_access_via_link_hidden = !!parseInt(event.target.value);
    }

    /**
     * @param {Event} event
     * @param {Proxy} accessPartner
     */
    onChangePartnerRole(event, accessPartner) {
        accessPartner.role = event.target.selectedOptions[0].value;
    }

    /**
     * @param {Proxy} accessPartner
     * @param {luxon.DateTime | Boolean } value
     */
    setExpirationDate(accessPartner, value) {
        accessPartner.expiration_date = value ? serializeDateTime(value) : value;
    }

    /**
     * Catch rpc response on update: error on document/folder or its access,
     * result on document tag creation
     */
    responseCall({ detail }) {
        if (detail.error && detail.data.params.model === "documents.document") {
            this.state.mainPage = true;
            this.revertChanges();
            this.state.loading = false;
        }
    }
}
