/** @odoo-module **/

import {
    registerClassPatchModel,
    registerInstancePatchModel,
} from '@mail/model/model_core';
import { insert } from '@mail/model/model_field_command';

registerClassPatchModel('mail.thread', 'im_livechat/static/src/models/thread/thread.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    /**
     * @override
     */
    convertData(data) {
        const additionalData2 = {};
        if ('livechat_visitor' in data && data.livechat_visitor && data.members) {
            const publicPartnerIds = new Set(this.env.messaging.publicPartners.map(partner => partner.id));
            data.members = data.members.map(memberData => {
                // `livechat_visitor` without `id` is the anonymous visitor.
                if (!data.livechat_visitor.id && publicPartnerIds.has(memberData.partner.id)) {
                    /**
                     * Create partner derived from public partner and replace the
                     * public partner.
                     *
                     * Indeed the anonymous visitor is registered as a member of the
                     * channel as the public partner in the database to avoid
                     * polluting the contact list with many temporary partners.
                     *
                     * But the issue with public partner is that it is the same
                     * record for every livechat, whereas every correspondent should
                     * actually have its own visitor name, typing status, etc.
                     *
                     * Due to JS being temporary by nature there is no such notion
                     * of polluting the database, it is therefore acceptable and
                     * easier to handle one temporary partner per channel.
                     */
                    const partnerData = Object.assign(
                        data.livechat_visitor,
                        { id: this.env.models['mail.partner'].getNextPublicId() },
                    );
                    memberData.partner = partnerData;
                    additionalData2.correspondent = insert(this.env.models['mail.partner'].convertData(partnerData));
                } else if (data.livechat_visitor.id === memberData.partner.id) {
                    memberData.partner = data.livechat_visitor;
                    additionalData2.correspondent = insert(this.env.models['mail.partner'].convertData(data.livechat_visitor));
                }
                return memberData;
            });
        }
        return Object.assign({}, this._super(data), additionalData2);
    },
});

registerInstancePatchModel('mail.thread', 'im_livechat/static/src/models/thread/thread.js', {

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _computeCorrespondent() {
        if (this.channel_type === 'livechat') {
            // livechat correspondent never change: always the public member.
            return;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeDisplayName() {
        if (this.channel_type === 'livechat' && this.correspondent) {
            if (this.correspondent.country) {
                return `${this.correspondent.nameOrDisplayName} (${this.correspondent.country.name})`;
            }
            return this.correspondent.nameOrDisplayName;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeIsChatChannel() {
        return this.channel_type === 'livechat' || this._super();
    },
});
