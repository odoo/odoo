odoo.define('mail.Many2OneAvatarUser', function (require) {
    "use strict";

    // This module defines an extension of the Many2OneAvatar widget, which is
    // integrated with the messaging system. The Many2OneAvatarUser is designed
    // to display people, and when the avatar of those people is clicked, it
    // opens a DM chat window with the corresponding partner (the messaging
    // system is based on model 'res.partner').
    //
    // This widget is supported on many2one fields pointing to 'res.users'. When
    // the user is clicked, we fetch the partner id of the given user (field
    // 'partner_id'), and we open a chat window with this partner.
    //
    // Usage:
    //   <field name="user_id" widget="many2one_avatar_user"/>
    //
    // The widget is designed to be extended, to support many2one fields pointing
    // to other models than 'res.users'. Those models must have a many2one field
    // pointing to 'res.partner'. Ideally, the many2one should be false if the
    // corresponding partner isn't associated with a user, otherwise it will open
    // chat windows with partners that won't be able to read your messages and
    // reply.

    const { _t } = require('web.core');
    const fieldRegistry = require('web.field_registry');
    const { Many2OneAvatar } = require('web.relational_fields');
    const session = require('web.session');


    const Many2OneAvatarUser = Many2OneAvatar.extend({
        events: Object.assign({}, Many2OneAvatar.prototype.events, {
            'click .o_m2o_avatar': '_onAvatarClicked',
        }),
        // Maps record ids to promises that resolve with the corresponding partner ids.
        // Used as a cache shared between all instances of this widget.
        partnerIds: {},
        // This widget is only supported on many2ones pointing to 'res.users'
        supportedModel: 'res.users',

        init() {
            this._super(...arguments);
            if (this.supportedModel !== this.field.relation) {
                throw new Error(`This widget is only supported on many2one fields pointing to ${this.supportedModel}`);
            }
            if (this.mode === 'readonly') {
                this.className += ' o_clickable_m2o_avatar';
            }
            this.partnerField = 'partner_id'; // field to read on 'res.users' to get the partner id
        },

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Displays a warning when we can't open a DM chat window with the partner
         * corresponding to the clicked record. On model 'res.users', it only
         * happens when the user clicked on himself. This can be overridden by
         * extensions of this widget, for instance to handle the case where the
         * user clicked on a record whose partner isn't associated with any user.
         *
         * @private
         */
        _displayWarning() {
            this.displayNotification({
                message: _t('You cannot chat with yourself'),
                type: 'info',
            });
        },
        /**
         * @private
         * @param {number} resId
         * @returns {string} the key to use in the partnerIds cache
         */
        _getCacheKey(resId) {
            return `${this.field.relation}_${resId}`;
        },
        /**
         * For a given record id of the comodel, returns the corresponding
         * partner id.
         *
         * @param {number} resId
         * @returns {Promise<integer|false>}
         */
        _resIdToPartnerId(resId) {
            const key = this._getCacheKey(resId);
            if (!this.partnerIds[key]) {
                const params = {
                    method: 'read',
                    model: this.field.relation,
                    args: [resId, [this.partnerField]],
                };
                this.partnerIds[key] = this._rpc(params).then(recs => {
                    const partner = recs[0][this.partnerField];
                    return partner && partner[0];
                });
            }
            return this.partnerIds[key];
        },

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * When the avatar is clicked, open a DM chat window with the
         * corresponding partner. If the user clicked on himself, open a blank
         * thread window, for the sake of consistency.
         *
         * @private
         * @param {MouseEvent} ev
         */
        async _onAvatarClicked(ev) {
            ev.stopPropagation(); // in list view, prevent from opening the record
            let partnerId;
            if (this.field.relation !== 'res.users' || this.value.res_id !== session.uid) {
                partnerId = await this._resIdToPartnerId(this.value.res_id);
            }
            if (partnerId && partnerId !== session.partner_id) {
                this.call('mail_service', 'openDMChatWindow', partnerId);
            } else {
                this._displayWarning(partnerId);
            }
        }
    });

    const KanbanMany2OneAvatarUser = Many2OneAvatarUser.extend({
        _template: 'mail.KanbanMany2OneAvatarUser',
    });

    fieldRegistry.add('many2one_avatar_user', Many2OneAvatarUser);
    fieldRegistry.add('kanban.many2one_avatar_user', KanbanMany2OneAvatarUser);

    return {
        Many2OneAvatarUser,
        KanbanMany2OneAvatarUser,
    };
});
