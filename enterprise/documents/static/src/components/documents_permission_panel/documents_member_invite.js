/** @odoo-module **/

import {
    DocumentsPermissionSelect,
    DocumentsPermissionSelectMenu,
} from "./documents_permission_select";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { rpcBus } from "@web/core/network/rpc";
import { useBus, useService } from "@web/core/utils/hooks";
import { isEmail } from "@web/core/utils/strings";
import { isEmpty } from "@html_editor/utils/dom_info";
import { Wysiwyg } from "@html_editor/wysiwyg";
import { HtmlMailField } from "@mail/views/web/fields/html_mail_field/html_mail_field";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillUpdateProps, useState } from "@odoo/owl";

const cssRulesByElement = new WeakMap();

export class DocumentsMemberInvite extends Component {
    static components = {
        DocumentsPermissionSelect,
        DocumentsPermissionSelectMenu,
        DropdownItem,
        Wysiwyg,
    };
    static props = {
        access: Object,
        accessPartners: Array,
        autoSave: Function,
        close: Function,
        selectedPartnersRole: String,
        invitePage: Boolean,
        disabled: Boolean,
        roles: Array,
        pendingSave: Boolean,
        showMainPage: Function,
        updateAccessRights: Function,
    };
    static template = "documents.MemberInvite";

    setup() {
        this.actionService = useService("action");
        this.createdPartners = { choices: [], values: [] };
        this.orm = useService("orm");
        this.state = useState({
            notify: true,
            fetchedPartners: [],
            selectedPartners: [],
            selectedPartnersRole: this.props.selectedPartnersRole,
            sharing: false,
        });
        const wysiwygPlaceholder = _t("Optional message...");
        this.wysiwyg = {
            config: {
                content: `<p placeholder="${wysiwygPlaceholder}"><br/></p>`,
                placeholder: wysiwygPlaceholder,
                disableVideo: true,
            },
            editor: undefined,
            message: "",
        };
        useBus(rpcBus, "RPC:RESPONSE", this.responseCall);

        onWillUpdateProps((nextProps) => {
            if (!nextProps.invitePage) {
                this.state.selectedPartners = [];
                this.state.selectedPartnersRole = this.props.selectedPartnersRole;
            }
        });
    }

    /**
     * @returns {string|undefined}
     */
    get noEditorMessage() {
        return undefined;
    }

    /**
     * @param {String} query
     * @param {Array} domain
     * @param {Number} limit
     * @returns Array[Object]
     */
    async getPartners(domain = [], limit = 4) {
        const partners = await this.orm.call("res.partner", "web_search_read", [], {
            domain: domain,
            specification: this._getPartnersSpecification(),
            limit: Math.max(limit, 8),  // Perf: lower bound of 8 for the limit, to hit trigram indexes
            count_limit: 1, // we don't need the number of records, skip the search_count
        });
        return partners.records.slice(0, limit);
    }

    _getPartnersSpecification() {
        return { display_name: 1, email: 1 };
    }

    /**
     * Call new contact form
     * @param {String} defaultName
     * @param {Boolean} andEdit
     */
    async createPartners(defaultName, andEdit = false) {
        const onClose = async () => {
            if (this.createdPartners.choices) {
                this.state.fetchedPartners = this.state.fetchedPartners.concat(
                    this.createdPartners.choices
                );
                this.state.selectedPartners = this.state.selectedPartners.concat(
                    this.createdPartners.values
                );
                this.props.showMainPage(false);
            }
        };
        if (andEdit) {
            return this.actionService.doActionButton({
                name: "action_create_members_to_invite",
                type: "object",
                resModel: "res.partner",
                buttonContext: {
                    default_name: defaultName,
                    dialog_size: "medium",
                },
                onClose,
            });
        }
        const partnerId = await this.orm.call("res.partner", "create", [
            {
                name: defaultName,
                email: defaultName,
            },
        ]);
        if (partnerId) {
            const createdPartners = await this.orm.webRead("res.partner", [partnerId], {
                specification: { name: 1, email: 1 },
            });
            this._addCreatedPartners(createdPartners);
        }
        await onClose();
    }

    /**
     * Provides a selection of partners based on user input
     * while keeping selected partners visible
     * @param {String} search
     */
    async onSearchPartners(search) {
        const selectedPartners = this.state.fetchedPartners.filter((p) =>
            this.state.selectedPartners.includes(p.id)
        );
        const partners = await this.getPartners([
            [
                "id",
                "!=",
                [
                    ...this.props.accessPartners.flatMap((a) => (a.role ? [a.partner_id.id] : [])),
                    ...selectedPartners.map((s) => s.id),
                    this.props.access.owner_id.partner_id?.id,
                ],
            ],
            "|",
            ["name", "ilike", search.trim()],
            ["email", "ilike", search.trim()],
        ]);
        this.state.fetchedPartners = [...partners, ...selectedPartners];
    }

    /**
     * Passed to SelectMenu in order to match found partners on display_name *and/or* email.
     * @param {{display_name: string, email: string}} partner
     * @return {string}
     */
    matchPartners(partner) {
        return `${partner.label} ${partner.email}`;
    }

    /**
     * @param {Event} event
     */
    onChangeRoleForMemberToInvite(event) {
        this.state.selectedPartnersRole = event.target.selectedOptions[0].value;
    }

    /**
     * @param {Number[]} values
     */
    onSelectPartnerToInvite(values) {
        this.state.selectedPartners = values;
        if (this.props.pendingSave) {
            this.props.autoSave();
        }
        if (!this.props.invitePage) {
            this.props.showMainPage(false);
        }
    }

    onClickNotify() {
        this.state.notify = !this.state.notify;
    }

    /**
     * Add new partner access to a document/folder
     */
    async onShare() {
        const partners = {};
        this.state.selectedPartners.forEach(
            (p) => (partners[p] = [this.state.selectedPartnersRole, false])
        );
        if (this.state.notify) {
            await this.getFormattedWysiwygContent();
        }
        this.state.sharing = true;
        await this.props.updateAccessRights(partners, this.state.notify, this.wysiwyg.message);
        await this.props.close();
    }

    /**
     * Switch back to the main page
     */
    onDiscard() {
        this.state.notify = true;
        this.props.showMainPage(true);
    }

    isEmail(value) {
        return isEmail(value);
    }

    /**
     * @param {Editor} editor
     */
    onLoadWysiwyg(editor) {
        this.wysiwyg.editor = editor;
    }

    /**
     * Format message content for email notification
     */
    async getFormattedWysiwygContent() {
        const el = this.wysiwyg.editor.getElContent();
        await HtmlMailField.getInlinedEditorContent(cssRulesByElement, this.wysiwyg.editor, el);
        this.wysiwyg.message = isEmpty(el.firstChild) ? "" : this.wysiwyg.editor.getContent();
    }

    /**
     * Catch rpc response to new contact creation request
     */
    responseCall({ detail }) {
        if (detail.result) {
            if (
                detail.data.params.method === "web_save" &&
                detail.data.params.model === "res.partner"
            ) {
                this._addCreatedPartners(detail.result);
            }
        }
    }

    _addCreatedPartners(createdPartners) {
        this.createdPartners = { choices: [], values: [] };
        for (const partner of createdPartners) {
            this.createdPartners.choices.push(this._addCreatedPartnersValues(partner));
            this.createdPartners.values.push(partner.id);
        }
    }

    _addCreatedPartnersValues(partner) {
        return {
            id: partner.id,
            display_name: partner.name,
            email: partner.email,
        };
    }
}
