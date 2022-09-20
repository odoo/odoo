/** @odoo-module **/

import core from 'web.core';
import fieldRegistry from 'web.field_registry';
import { FieldMany2ManyTagsAvatar, Many2OneAvatar, KanbanMany2ManyTagsAvatar } from 'web.relational_fields';
import session from 'web.session';

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
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Opens a chat window with the given user id.
     *
     * @private
     * @param {Object} params
     */
    async _openChat(params) {
        const messaging = await Component.env.services.messaging.get();
        messaging.openChat(params);
    },
};

export const Many2OneAvatarUser = Many2OneAvatar.extend(M2XAvatarMixin, {
    events: Object.assign({}, Many2OneAvatar.prototype.events, {
        'click .o_m2o_avatar > img': '_onAvatarClicked',
    }),

    on_attach_callback() {
        this._registerCommandAssignTo()
    },
    on_detach_callback(){
        this._unregisterCommandAssignTo()
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
     _registerCommandAssignTo() {
        const self = this;
        if (self.viewType === "form") {
            let provide = async (env, options) => {
                if (self.isDestroyed()) {
                    return
                }
                const records = await self._searchAssignTo(options.searchValue, 10)
                return records.map((record) => ({
                    name: record[1],
                    action: () => {
                        if (self.isDestroyed()) {
                            return
                        }
                        self.reinitialize({ id: record[0], display_name: record[1] });
                    }
                }))
            }
            let getCommandDefinition = (env) => ({
                name: env._t("Assign to ..."),
                options: {
                    activeElement: env.services.ui.getActiveElementOf(self.el),
                    category: "smart_action",
                    hotkey: "alt+i",
                },
                async action() {
                    return {
                        configByNamespace: {
                            default: {
                                emptyMessage: env._t("No users found"),
                            },
                        },
                        placeholder: env._t("Select a user..."),
                        providers: [{ provide }],
                    };
                },
            });
            core.bus.trigger("set_legacy_command", "web.Many2OneAvatar.assignTo", getCommandDefinition, self.el);


            getCommandDefinition = (env) => ({
                name: env._t("Assign/unassign to me"),
                options: {
                    activeElement: env.services.ui.getActiveElementOf(self.el),
                    category: "smart_action",
                    hotkey: "alt+shift+i",
                },
                action() {
                    if (self.isDestroyed()) {
                        return
                    }
                    if (self.value.res_id === session.user_id[0]) {
                        self._setValue({
                            operation: 'DELETE',
                            ids: [session.user_id[0]],
                            });
                    } else {
                        self.reinitialize({ id: session.user_id[0], display_name: session.name });
                    }
                },
            });
            core.bus.trigger("set_legacy_command", "web.Many2OneAvatar.assignToMe", getCommandDefinition);
        }
    },

    /**
     * @override
     * @private
     */
    _unregisterCommandAssignTo() {
        core.bus.trigger("remove_legacy_command", "web.Many2OneAvatar.assignTo");
        core.bus.trigger("remove_legacy_command", "web.Many2OneAvatar.assignToMe");
    },

    /**
     * @override
     * @private
     */
    _searchAssignTo(searchValue, limit) {
        const value = searchValue.trim();
        const domain = this.record.getDomain(this.recordParams);
        const context = Object.assign(
            this.record.getContext(this.recordParams),
            this.additionalContext,
        );

        // Exclude black-listed ids from the domain
        const blackListedIds = this._getSearchBlacklist();
        if (blackListedIds.length) {
            domain.push(['id', 'not in', blackListedIds]);
        }

        const nameSearch = this._rpc({
            model: this.field.relation,
            method: "name_search",
            kwargs: {
                name: value,
                args: domain,
                operator: "ilike",
                limit: limit + 1,
                context,
            }
        });
        return this.orderer.add(nameSearch);
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
    _onAvatarClicked(ev) {
        ev.stopPropagation(); // in list view, prevent from opening the record
        this._openChat({ userId: this.value.res_id });
    }
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

export const Many2ManyAvatarUser = FieldMany2ManyTagsAvatar.extend(M2MAvatarMixin, {

    on_attach_callback() {
        this._registerCommandAssignTo()
    },
    on_detach_callback(){
        this._unregisterCommandAssignTo()
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
     _registerCommandAssignTo() {
        const self = this;
        if (self.viewType === "form") {
            const provide = async (env, options) => {
                if (self.isDestroyed()) {
                    return
                }
                const many2one = new Many2OneAvatarUser(self, self.name, self.record, {
                    mode: 'edit',
                    noOpen: true,
                    noCreate: !self.canCreate,
                    viewType: self.viewType,
                    attrs: self.attrs,
                });
                many2one._getSearchBlacklist = function () {
                    return self.value.res_ids;
                };
                const records = await many2one._searchAssignTo(options.searchValue, 10)
                return records.map((record) => ({
                    name: record[1],
                    action: () => {
                        if (self.isDestroyed()) {
                            return
                        }
                        self._setValue({
                            operation: 'ADD_M2M',
                            ids: { id: record[0], display_name: record[1] }
                        });
                    },
                }))
            };
            let getCommandDefinition = (env) => ({
                name: env._t("Assign to ..."),
                options: {
                    activeElement: env.services.ui.getActiveElementOf(self.el),
                    category: "smart_action",
                    hotkey: "alt+i",
                },
                action() {
                    return {
                        configByNamespace: {
                            default: {
                                emptyMessage: env._t("No users found"),
                            },
                        },
                        placeholder: env._t("Select a user..."),
                        providers: [{ provide }],
                    };
                },
            });
            core.bus.trigger("set_legacy_command", "web.FieldMany2ManyTagsAvatar.assignTo", getCommandDefinition)

            getCommandDefinition = (env) => ({
                name: env._t("Assign/unassign to me"),
                options: {
                    activeElement: env.services.ui.getActiveElementOf(self.el),
                    category: "smart_action",
                    hotkey: "alt+shift+i",
                },
                action() {
                    if (self.isDestroyed()) {
                        return
                    }
                    if (self.value.res_ids.includes(session.user_id[0])) {
                        self._setValue({
                            operation: 'DELETE',
                            ids: [session.user_id[0]],
                            });
                    } else {
                        self._setValue({
                            operation: 'ADD_M2M',
                            ids: { id:  session.user_id[0], display_name: session.name }
                        });
                    }
                },
            });
            core.bus.trigger("set_legacy_command", "web.Many2OneAvatar.assignToMe", getCommandDefinition);
        }
    },

    /**
     * @override
     * @private
     */
     _unregisterCommandAssignTo() {
        core.bus.trigger("remove_legacy_command", "web.FieldMany2ManyTagsAvatar.assignTo");
        core.bus.trigger("remove_legacy_command", "web.Many2OneAvatar.assignToMe");
     }
});

export const KanbanMany2OneAvatarUser = Many2OneAvatarUser.extend({
    _template: 'mail.KanbanMany2OneAvatarUser',

    init() {
        this._super(...arguments);
        this.displayAvatarName = this.nodeOptions.display_avatar_name || false;
    },
});
export const KanbanMany2ManyAvatarUser = KanbanMany2ManyTagsAvatar.extend(M2MAvatarMixin, {});

fieldRegistry.add('many2one_avatar_user', Many2OneAvatarUser);
fieldRegistry.add('activity.many2one_avatar_user', KanbanMany2OneAvatarUser);
fieldRegistry.add('many2many_avatar_user', Many2ManyAvatarUser);
