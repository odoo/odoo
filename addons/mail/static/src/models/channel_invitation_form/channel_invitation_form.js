/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2one } from '@mail/model/model_field';
import { clear, insertAndReplace, link, replace, unlink, unlinkAll } from '@mail/model/model_field_command';
import { cleanSearchTerm } from '@mail/utils/utils';

function factory(dependencies) {

    class ChannelInvitationForm extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickInvite = this.onClickInvite.bind(this);
            this.onInputSearch = this.onInputSearch.bind(this);
        }
        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Handles click on the "invite" button.
         *
         * @param {MouseEvent} ev
         */
        async onClickInvite(ev) {
            if (this.thread.channel_type === 'chat') {
                const partners_to = [...new Set([
                    this.messaging.currentPartner.id,
                    ...this.thread.members.map(member => member.id),
                    ...this.selectedPartners.map(partner => partner.id),
                ])];
                const channel = await this.messaging.models['mail.thread'].createGroupChat({ partners_to });
                if (this.thread.rtc) {
                    /**
                     * if we were in a RTC call on the current thread, we move to the new group chat.
                     * A smoother transfer would be moving the RTC sessions from one channel to
                     * the other (server-side too), but it would be considerably more complex.
                     */
                    await this.async(() => channel.toggleCall({
                        startWithVideo: !!this.thread.rtc.videoTrack,
                        videoType: this.thread.rtc.sendUserVideo ? 'user-video' : 'display',
                    }));
                }
                channel.open();
            } else {
                await this.env.services.rpc(({
                    model: 'mail.channel',
                    method: 'add_members',
                    args: [[this.thread.id]],
                    kwargs: {
                        partner_ids: this.selectedPartners.map(partner => partner.id),
                        invite_to_rtc_call: !!this.thread.rtc,
                    },
                }));
            }
            this.update({
                searchTerm: "",
                selectedPartners: unlinkAll(),
            });
            this.delete();
        }

        /**
         * @param {mail.partner} partner
         * @param {MouseEvent} ev
         */
        onClickSelectablePartner(partner, ev) {
            if (this.selectedPartners.includes(partner)) {
                this.update({ selectedPartners: unlink(partner) });
                return;
            }
            this.update({ selectedPartners: link(partner) });
        }

        /**
         * @param {mail.partner} partner
         * @param {MouseEvent} ev
         */
        onClickSelectedPartner(partner, ev) {
            this.update({ selectedPartners: unlink(partner) });
        }

        /**
         * Handles OWL update on this channel invitation form component.
         */
        onComponentUpdate() {
            if (this.doFocusOnSearchInput && this.searchInputRef.el) {
                this.searchInputRef.el.focus();
                this.searchInputRef.el.setSelectionRange(this.searchTerm.length, this.searchTerm.length);
                this.update({ doFocusOnSearchInput: clear() });
            }
        }

        /**
         * @param {mail.partner} partner
         * @param {InputEvent} ev
         */
        onInputPartnerCheckbox(partner, ev) {
            if (!ev.target.checked) {
                this.update({ selectedPartners: unlink(partner) });
                return;
            }
            this.update({ selectedPartners: link(partner) });
        }

        /**
         * @param {InputEvent} ev
         */
        async onInputSearch(ev) {
            this.update({ searchTerm: ev.target.value });
            this.searchPartnersToInvite();
        }

        /**
         * Searches for partners to invite based on the current search term. If
         * a search is already in progress, waits until it is done to start a
         * new one.
         */
        async searchPartnersToInvite() {
            if (this.hasSearchRpcInProgress) {
                this.update({ hasPendingSearchRpc: true });
                return;
            }
            this.update({
                hasPendingSearchRpc: false,
                hasSearchRpcInProgress: true,
            });
            try {
                const channelId = (this.thread && this.thread.model === 'mail.channel') ? this.thread.id : undefined;
                const { count, partners: partnersData } = await this.env.services.rpc(
                    {
                        model: 'res.partner',
                        method: 'search_for_channel_invite',
                        kwargs: {
                            channel_id: channelId,
                            search_term: cleanSearchTerm(this.searchTerm),
                        },
                    },
                    { shadow: true }
                );
                if (!this.exists()) {
                    return;
                }
                this.update({
                    searchResultCount: count,
                    selectablePartners: insertAndReplace(partnersData.map(partnerData => this.messaging.models['mail.partner'].convertData(partnerData))),
                });
            } finally {
                if (this.exists()) {
                    this.update({ hasSearchRpcInProgress: false });
                    if (this.hasPendingSearchRpc) {
                        this.searchPartnersToInvite();
                    }
                }
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeInviteButtonText() {
            if (!this.thread) {
                return clear();
            }
            switch (this.thread.channel_type) {
                case 'chat':
                    return this.env._t("Create group chat");
                case 'group':
                    return this.env._t("Invite to group chat");
            }
            return this.env._t("Invite to Channel");
        }

        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThread() {
            if (this.threadView && this.threadView.thread) {
                return replace(this.threadView.thread);
            }
            if (this.chatWindow && this.chatWindow.thread) {
                return replace(this.chatWindow.thread);
            }
            return clear();
        }

    }

    ChannelInvitationForm.fields = {
        chatWindow: one2one('mail.chat_window', {
            inverse: 'channelInvitationForm',
            readonly: true,
        }),
        /**
         * States the OWL component of this channel invitation form.
         * Useful to be able to close it with popover trigger, or to know when
         * it is open to update the button active state.
         */
        component: attr(),
        /**
         * Determines whether this search input needs to be focused.
         */
        doFocusOnSearchInput: attr(),
        /**
         * States whether there is a pending search RPC.
         */
        hasPendingSearchRpc: attr({
            default: false,
        }),
        /**
         * States whether there is search RPC in progress.
         */
        hasSearchRpcInProgress: attr({
            default: false,
        }),
        /**
         * Determines the text of the invite button.
         */
        inviteButtonText: attr({
            compute: '_computeInviteButtonText',
        }),
        popoverView: one2one('mail.popover_view', {
            inverse: 'channelInvitationForm',
            isCausal: true,
        }),
        /**
         * States the OWL ref of the "search" input of this channel invitation
         * form. Useful to be able to focus it.
         */
        searchInputRef: attr(),
        /**
         * States the number of results of the last search.
         */
        searchResultCount: attr({
            default: 0,
        }),
        /**
         * Determines the search term used to filter this list.
         */
        searchTerm: attr({
            default: "",
        }),
        /**
         * States all partners that are potential choices according to this
         * search term.
         */
        selectablePartners: many2many('mail.partner'),
        /**
         * Determines all partners that are currently selected.
         */
        selectedPartners: many2many('mail.partner'),
        /**
         * States the thread on which this list operates (if any).
         */
        thread: many2one('mail.thread', {
            compute: '_computeThread',
            readonly: true,
            required: true,
        }),
        /**
         * States the thread view on which this list operates (if any).
         */
        threadView: one2one('mail.thread_view', {
            inverse: 'channelInvitationForm',
            readonly: true,
        }),
    };
    ChannelInvitationForm.identifyingFields = [['chatWindow', 'threadView']];
    ChannelInvitationForm.modelName = 'mail.channel_invitation_form';

    return ChannelInvitationForm;
}

registerNewModel('mail.channel_invitation_form', factory);
