/** @odoo-module alias=mailing.PortalSubscriptionBlocklist **/

import { rpc } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";


publicWidget.registry.MailingPortalSubscriptionBlocklist = publicWidget.Widget.extend({
    events: {
        'click #button_blocklist_add': '_onBlocklistAddClick',
        'click #button_blocklist_remove': '_onBlocklistRemoveClick',
    },

    /**
     * @override
     */
    init: function (parent, options) {
        this.customerData = options.customerData;
        return this._super.apply(this, arguments);
    },

    /**
     * @override
     */
    start: function () {
        this._updateDisplay();
        return this._super.apply(this, arguments);
    },

    /*
     * Triggers call to add current email in blocklist. Update widget internals
     * and DOM accordingly (buttons display mainly). Bubble up to let parent
     * handle returned result if necessary.
     */
    _onBlocklistAddClick: async function (event) {
        event.preventDefault();
        return await rpc(
            '/mailing/blocklist/add',
            {
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                hash_token: this.customerData.hashToken,
                mailing_id: this.customerData.mailingId,
            }
        ).then((result) => {
            if (result === true) {
                this.customerData.isBlocklisted = true;
            }
            this._updateDisplay();
            this._updateInfo(result === true ? 'blocklist_add' : 'error');
            this.trigger_up(
                'blocklist_add',
                {'callKey': result === true ? 'blocklist_add' : result,
                 'isBlocklisted': result === true ? true: this.customerData.isBlocklisted,
                },
            );
        });
    },

    /*
     * Triggers call to remove current email from blocklist. Update widget
     * internals and DOM accordingly (buttons display mainly). Bubble up to let
     * parent handle returned result if necessary.
     */
    _onBlocklistRemoveClick: async function (event) {
        event.preventDefault();
        return await rpc(
            '/mailing/blocklist/remove',
            {
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                hash_token: this.customerData.hashToken,
                mailing_id: this.customerData.mailingId,
            }
        ).then((result) => {
            if (result === true) {
                this.customerData.isBlocklisted = false;
            }
            this._updateDisplay();
            this._updateInfo(result === true ? 'blocklist_remove' : 'error');
            this.trigger_up(
                'blocklist_remove',
                {'callKey': result === true ? 'blocklist_remove' : result,
                 'isBlocklisted': result === true ? false: this.customerData.isBlocklisted,
                },
            );
        });
    },

    /*
     * Display buttons and info according to current state. Removing from blocklist
     * is always available when being blocklisted. Adding in blocklist is available
     * when not being blocklisted, if the action is possible (valid email mainly)
     * and if the option is activated.
     */
    _updateDisplay: function () {
        const buttonAddNode = document.getElementById('button_blocklist_add');
        const buttonRemoveNode = document.getElementById('button_blocklist_remove');
        if (this.customerData.blocklistEnabled && this.customerData.blocklistPossible && !this.customerData.isBlocklisted) {
            buttonAddNode.classList.remove('d-none');
        } else {
            buttonAddNode.classList.add('d-none');
        }
        if (this.customerData.isBlocklisted) {
            buttonRemoveNode.classList.remove('d-none');
        } else {
            buttonRemoveNode.classList.add('d-none');
        }
    },

    /*
     * Display feedback (visual tips) to the user concerning the last done action.
     */
    _updateInfo: function (infoKey) {
        const updateInfo = document.getElementById('o_mailing_subscription_update_info');
        if (infoKey !== undefined) {
            const infoContent = renderToElement(
                "mass_mailing.portal.blocklist_update_info",
                {
                    infoKey: infoKey,
                }
            );
            updateInfo.innerHTML = infoContent.innerHTML;
            if (['blocklist_add', 'blocklist_remove'].includes(infoKey)) {
                updateInfo.classList.add('text-success');
                updateInfo.classList.remove('text-danger');
            }
            else {
                updateInfo.classList.add('text-danger');
                updateInfo.classList.remove('text-success');
            }
            updateInfo.classList.remove('d-none');
        }
        else {
            updateInfo.classList.add('d-none');
        }
    },
});

export default publicWidget.registry.MailingPortalSubscriptionBlocklist;
