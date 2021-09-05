/** @odoo-module **/

import fieldRegistry from 'web.field_registry';
import { Many2OneAvatar } from 'web.relational_fields';
import { FieldMany2ManyTagsAvatar, KanbanMany2ManyTagsAvatar, ListMany2ManyTagsAvatar } from 'web.relational_fields';

const { Component } = owl;


// This module defines extensions of the Many2OneAvatar and Many2ManyAvatar
// widgets, which are integrated with the messaging system. They are designed
// to display people, and when the avatar of those people is clicked, it
// opens a DM chat window with the corresponding user.
//
// These widgets are supported on many2one and many2many fields pointing to
// 'res.users'.
//
// Usage:
//   <field name="user_id" widget="many2one_avatar_user"/>
//
// The widgets are designed to be extended, to support fields pointing to other
// models than 'res.users'.

const M2XAvatarMixin = {
    supportedModels: ['res.users'],

    init() {
        this._super(...arguments);
        if (!this.supportedModels.includes(this.field.relation)) {
            throw new Error(`This widget is only supported on many2one and many2many fields pointing to ${JSON.stringify(this.supportedModels)}`);
        }
        this.className = `${this.className || ''} o_clickable_m2x_avatar`.trim();
        this.noOpenChat = this.nodeOptions.no_open_chat || false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Opens a chat window with the given user id.
     *
     * @private
     * @param {Object} params
     * @returns {Promise}
     */
    async _openChat(params) {
        if (!this.noOpenChat) {
            const messaging = await Component.env.services.messaging.get();
            return messaging.openChat(params);
        }
        return Promise.resolve();
    },
};

export const Many2OneAvatarUser = Many2OneAvatar.extend(M2XAvatarMixin, {
    events: Object.assign({}, Many2OneAvatar.prototype.events, {
        'click .o_m2o_avatar > img': '_onAvatarClicked',
    }),

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
    _onAvatarClicked(ev) {
        ev.stopPropagation(); // in list view, prevent from opening the record
        this._openChat({ userId: this.value.res_id });
    },
});

export const KanbanMany2OneAvatarUser = Many2OneAvatarUser.extend({
    _template: 'mail.KanbanMany2OneAvatarUser',
});

const M2MAvatarMixin = Object.assign(M2XAvatarMixin, {
    events: Object.assign({}, FieldMany2ManyTagsAvatar.prototype.events, {
        'click .o_m2m_avatar': '_onAvatarClicked',
    }),

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAvatarClicked(ev) {
        ev.stopPropagation(); // in list view, prevent from opening the record
        const userId = parseInt(ev.target.getAttribute('data-id'), 10);
        this._openChat({ userId: userId });
    },
});

export const Many2ManyAvatarUser = FieldMany2ManyTagsAvatar.extend(M2MAvatarMixin, {});

export const KanbanMany2ManyAvatarUser = KanbanMany2ManyTagsAvatar.extend(M2MAvatarMixin, {});

export const ListMany2ManyAvatarUser = ListMany2ManyTagsAvatar.extend(M2MAvatarMixin, {});

fieldRegistry.add('many2one_avatar_user', Many2OneAvatarUser);
fieldRegistry.add('kanban.many2one_avatar_user', KanbanMany2OneAvatarUser);
fieldRegistry.add('activity.many2one_avatar_user', KanbanMany2OneAvatarUser);
fieldRegistry.add('many2many_avatar_user', Many2ManyAvatarUser);
fieldRegistry.add('kanban.many2many_avatar_user', KanbanMany2ManyAvatarUser);
fieldRegistry.add('list.many2many_avatar_user', ListMany2ManyAvatarUser);
