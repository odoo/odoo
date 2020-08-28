odoo.define('mail.Many2OneAvatarUser', function (require) {
    "use strict";

    // This module defines an extension of the Many2OneAvatar widget, which is
    // integrated with the messaging system. The Many2OneAvatarUser is designed
    // to display people, and when the avatar of those people is clicked, it
    // opens a DM chat window with the corresponding user.
    //
    // This widget is supported on many2one fields pointing to 'res.users'.
    //
    // Usage:
    //   <field name="user_id" widget="many2one_avatar_user"/>
    //
    // The widget is designed to be extended, to support many2one fields pointing
    // to other models than 'res.users'.

    const fieldRegistry = require('web.field_registry');
    const { Many2OneAvatar } = require('web.relational_fields');

    const { Component } = owl;

    const Many2OneAvatarUser = Many2OneAvatar.extend({
        events: Object.assign({}, Many2OneAvatar.prototype.events, {
            'click .o_m2o_avatar': '_onAvatarClicked',
        }),
        // This widget is only supported on many2ones pointing to 'res.users'
        supportedModels: ['res.users'],

        init() {
            this._super(...arguments);
            if (!this.supportedModels.includes(this.field.relation)) {
                throw new Error(`This widget is only supported on many2one fields pointing to ${JSON.stringify(this.supportedModels)}`);
            }
            if (this.mode === 'readonly') {
                this.className += ' o_clickable_m2o_avatar';
            }
        },

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * When the avatar is clicked, open a DM chat window with the
         * corresponding user.
         *
         * @private
         * @param {MouseEvent} ev
         */
        async _onAvatarClicked(ev) {
            ev.stopPropagation(); // in list view, prevent from opening the record
            const env = Component.env;
            await env.messaging.openChat({ userId: this.value.res_id });
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
