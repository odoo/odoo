/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, link, unlink } from '@mail/model/model_field_command';
import { cleanSearchTerm } from '@mail/utils/utils';

import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'ChannelInvitationForm',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * Handles click on the "copy" button.
         *
         * @param {MouseEvent} ev
         */
        async onClickCopy(ev) {
            await navigator.clipboard.writeText(this.thread.invitationLink);
            this.messaging.notify({
                message: this.env._t('Link copied!'),
                type: 'success',
            });
        },
        /**
         * Handles click on the "invite" button.
         *
         * @param {MouseEvent} ev
         */
        async onClickInvite(ev) {
            if (this.thread.channel.channel_type === 'chat') {
                const partners_to = [...new Set([
                    this.messaging.currentPartner.id,
                    ...this.thread.channel.channelMembers.filter(member => member.persona && member.persona.partner).map(member => member.persona.partner.id),
                    ...this.selectedPartners.map(partner => partner.id),
                ])];
                const channel = await this.messaging.models['Thread'].createGroupChat({ partners_to });
                if (this.thread.rtc) {
                    /**
                     * if we were in a RTC call on the current thread, we move to the new group chat.
                     * A smoother transfer would be moving the RTC sessions from one channel to
                     * the other (server-side too), but it would be considerably more complex.
                     */
                    await channel.toggleCall({
                        startWithVideo: !!this.thread.rtc.videoTrack,
                        videoType: this.thread.rtc.sendUserVideo ? 'user-video' : 'display',
                    });
                }
                if (channel.exists()) {
                    channel.open();
                }
            } else {
                await this.messaging.rpc(({
                    model: 'mail.channel',
                    method: 'add_members',
                    args: [[this.thread.id]],
                    kwargs: {
                        partner_ids: this.selectedPartners.map(partner => partner.id),
                        invite_to_rtc_call: !!this.thread.rtc,
                    },
                }));
            }
            if (this.exists()) {
                this.delete();
            }
        },
        /**
         * @param {Partner} partner
         */
        onClickSelectablePartner(partner) {
            if (this.selectedPartners.includes(partner)) {
                this.update({ selectedPartners: unlink(partner) });
                return;
            }
            this.update({ selectedPartners: link(partner) });
        },
        /**
         * @param {Partner} partner
         */
        onClickSelectedPartner(partner) {
            this.update({ selectedPartners: unlink(partner) });
        },
        /**
         * Handles OWL update on this channel invitation form component.
         */
        onComponentUpdate() {
            if (this.doFocusOnSearchInput && this.searchInputRef.el) {
                this.searchInputRef.el.focus();
                this.searchInputRef.el.setSelectionRange(this.searchTerm.length, this.searchTerm.length);
                this.update({ doFocusOnSearchInput: clear() });
            }
        },
        /**
         * Handles focus on the invitation link.
         */
        onFocusInvitationLinkInput(ev) {
            ev.target.select();
        },
        /**
         * @param {Partner} partner
         * @param {InputEvent} ev
         */
        onInputPartnerCheckbox(partner, ev) {
            if (!ev.target.checked) {
                this.update({ selectedPartners: unlink(partner) });
                return;
            }
            this.update({ selectedPartners: link(partner) });
        },
        /**
         * @param {InputEvent} ev
         */
        async onInputSearch(ev) {
            this.update({ searchTerm: ev.target.value });
            this.searchPartnersToInvite();
        },
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
                const { count, partners: partnersData } = await this.messaging.rpc(
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
                    selectablePartners: partnersData,
                });
            } finally {
                if (this.exists()) {
                    this.update({ hasSearchRpcInProgress: false });
                    if (this.hasPendingSearchRpc) {
                        this.searchPartnersToInvite();
                    }
                }
            }
        },
    },
    fields: {
        accessRestrictedToGroupText: attr({
            compute() {
                if (!this.thread) {
                    return clear();
                }
                if (!this.thread.authorizedGroupFullName) {
                    return clear();
                }
                return sprintf(
                    this.env._t('Access restricted to group "%(groupFullName)s"'),
                    { 'groupFullName': this.thread.authorizedGroupFullName }
                );
            },
        }),
        chatWindow: one('ChatWindow', {
            identifying: true,
            inverse: 'channelInvitationForm',
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
            compute() {
                if (!this.thread || !this.thread.channel) {
                    return clear();
                }
                switch (this.thread.channel.channel_type) {
                    case 'chat':
                        return this.env._t("Create group chat");
                    case 'group':
                        return this.env._t("Invite to group chat");
                }
                return this.env._t("Invite to Channel");
            },
        }),
        /**
         * If set, this channel invitation form is content of related popover view.
         */
        popoverViewOwner: one('PopoverView', {
            identifying: true,
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
        selectablePartners: many('Partner'),
        selectablePartnerViews: many('ChannelInvitationFormSelectablePartnerView', {
            compute() {
                if (this.selectablePartners.length === 0) {
                    return clear();
                }
                return this.selectablePartners.map(partner => ({ partner }));
            },
            inverse: 'channelInvitationFormOwner',
        }),
        /**
         * Determines all partners that are currently selected.
         */
        selectedPartners: many('Partner'),
        selectedPartnerViews: many('ChannelInvitationFormSelectedPartnerView', {
            compute() {
                if (this.selectedPartners.length === 0) {
                    return clear();
                }
                return this.selectedPartners.map(partner => ({ partner }));
            },
            inverse: 'channelInvitationFormOwner',
        }),
        /**
         * States the thread on which this list operates (if any).
         */
        thread: one('Thread', {
            compute() {
                if (
                    this.popoverViewOwner &&
                    this.popoverViewOwner.threadViewTopbarOwnerAsInvite &&
                    this.popoverViewOwner.threadViewTopbarOwnerAsInvite.thread
                ) {
                    return this.popoverViewOwner.threadViewTopbarOwnerAsInvite.thread;
                }
                if (this.chatWindow && this.chatWindow.thread) {
                    return this.chatWindow.thread;
                }
                return clear();
            },
            required: true,
        }),
    },
});
