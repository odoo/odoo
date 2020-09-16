odoo.define('mail/static/src/models/follower.follower.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class Follower extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} data
         * @returns {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('channel_id' in data) {
                if (!data.channel_id) {
                    data2.__mfield_channel = [['unlink-all']];
                } else {
                    const channelData = {
                        __mfield_id: data.channel_id,
                        __mfield_model: 'mail.channel',
                        __mfield_name: data.name,
                    };
                    data2.__mfield_channel = [['insert', channelData]];
                }
            }
            if ('id' in data) {
                data2.__mfield_id = data.id;
            }
            if ('is_active' in data) {
                data2.__mfield_isActive = data.is_active;
            }
            if ('is_editable' in data) {
                data2.__mfield_isEditable = data.is_editable;
            }
            if ('partner_id' in data) {
                if (!data.partner_id) {
                    data2.__mfield_partner = [['unlink-all']];
                } else {
                    const partnerData = {
                        __mfield_email: data.email,
                        __mfield_id: data.partner_id,
                        __mfield_name: data.name,
                    };
                    data2.__mfield_partner = [['insert', partnerData]];
                }
            }
            return data2;
        }

        /**
         *  Close subtypes dialog
         */
        closeSubtypes() {
            this._subtypesListDialog.delete();
            this._subtypesListDialog = undefined;
        }

        /**
         * Opens the most appropriate view that is a profile for this follower.
         */
        async openProfile() {
            if (this.__mfield_partner(this)) {
                return this.__mfield_partner(this).openProfile();
            }
            return this.__mfield_channel(this).openProfile();
        }

        /**
         * Remove this follower from its related thread.
         */
        async remove() {
            const partner_ids = [];
            const channel_ids = [];
            if (this.__mfield_partner(this)) {
                partner_ids.push(this.__mfield_partner(this).__mfield_id(this));
            } else {
                channel_ids.push(this.__mfield_channel(this).__mfield_id(this));
            }
            await this.async(() => this.env.services.rpc({
                model: this.__mfield_followedThread(this).__mfield_model(this),
                method: 'message_unsubscribe',
                args: [[this.__mfield_followedThread(this).__mfield_id(this)], partner_ids, channel_ids]
            }));
            const followedThread = this.__mfield_followedThread(this);
            this.delete();
            followedThread.fetchAndUpdateSuggestedRecipients();
        }

        /**
         * @param {mail.follower_subtype} subtype
         */
        selectSubtype(subtype) {
            if (!this.__mfield_selectedSubtypes(this).includes(subtype)) {
                this.update({
                    __mfield_selectedSubtypes: [['link', subtype]],
                });
            }
        }

        /**
         * Show (editable) list of subtypes of this follower.
         */
        async showSubtypes() {
            const subtypesData = await this.async(() => this.env.services.rpc({
                route: '/mail/read_subscription_data',
                params: {
                    follower_id: this.__mfield_id(this),
                },
            }));
            this.update({
                __mfield_subtypes: [['unlink-all']],
            });
            for (const data of subtypesData) {
                const subtype = this.env.models['mail.follower_subtype'].insert(
                    this.env.models['mail.follower_subtype'].convertData(data)
                );
                this.update({
                    __mfield_subtypes: [['link', subtype]],
                });
                if (data.followed) {
                    this.update({
                        __mfield_selectedSubtypes: [['link', subtype]],
                    });
                } else {
                    this.update({
                        __mfield_selectedSubtypes: [['unlink', subtype]],
                    });
                }
            }
            this._subtypesListDialog = this.env.messaging.__mfield_dialogManager(this).open('mail.follower_subtype_list', {
                __mfield_follower: [['link', this]],
            });
        }

        /**
         * @param {mail.follower_subtype} subtype
         */
        unselectSubtype(subtype) {
            if (this.__mfield_selectedSubtypes(this).includes(subtype)) {
                this.update({
                    __mfield_selectedSubtypes: [['unlink', subtype]],
                });
            }
        }

        /**
         * Update server-side subscription of subtypes of this follower.
         */
        async updateSubtypes() {
            if (this.__mfield_selectedSubtypes(this).length === 0) {
                this.remove();
            } else {
                const kwargs = {
                    subtype_ids: this.__mfield_selectedSubtypes(this).map(subtype => subtype.__mfield_id(this)),
                };
                if (this.__mfield_partner(this)) {
                    kwargs.partner_ids = [this.__mfield_partner(this).__mfield_id(this)];
                } else {
                    kwargs.channel_ids = [this.__mfield_channel(this).__mfield_id(this)];
                }
                await this.async(() => this.env.services.rpc({
                    model: this.__mfield_followedThread(this).__mfield_model(this),
                    method: 'message_subscribe',
                    args: [[this.__mfield_followedThread(this).__mfield_id(this)]],
                    kwargs,
                }));
            }
            this.closeSubtypes();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.__mfield_id}`;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeName() {
            if (this.__mfield_channel(this)) {
                return this.__mfield_channel(this).__mfield_name(this);
            }
            if (this.__mfield_partner(this)) {
                return this.__mfield_partner(this).__mfield_name(this);
            }
            return '';
        }

        /**
         * @private
         * @returns {integer}
         */
        _computeResId() {
            if (this.__mfield_partner(this)) {
                return this.__mfield_partner(this).__mfield_id(this);
            }
            if (this.__mfield_channel(this)) {
                return this.__mfield_channel(this).__mfield_id(this);
            }
            return 0;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeResModel() {
            if (this.__mfield_partner(this)) {
                return this.__mfield_partner(this).__mfield_model(this);
            }
            if (this.__mfield_channel(this)) {
                return this.__mfield_channel(this).__mfield_model(this);
            }
            return '';
        }

    }

    Follower.fields = {
        __mfield_resId: attr({
            compute: '_computeResId',
            default: 0,
            dependencies: [
                '__mfield_channelId',
                '__mfield_partnerId',
            ],
        }),
        __mfield_channel: many2one('mail.thread'),
        __mfield_channelId: attr({
            related: '__mfield_channel.__mfield_id',
        }),
        __mfield_channelModel: attr({
            related: '__mfield_channel.__mfield_model',
        }),
        __mfield_channelName: attr({
            related: '__mfield_channel.__mfield_name',
        }),
        __mfield_followedThread: many2one('mail.thread', {
            inverse: '__mfield_followers',
        }),
        __mfield_id: attr(),
        __mfield_isActive: attr({
            default: true,
        }),
        __mfield_isEditable: attr({
            default: false,
        }),
        __mfield_name: attr({
            compute: '_computeName',
            dependencies: [
                '__mfield_channelName',
                '__mfield_partnerName',
            ],
        }),
        __mfield_partner: many2one('mail.partner'),
        __mfield_partnerId: attr({
            related: '__mfield_partner.__mfield_id',
        }),
        __mfield_partnerModel: attr({
            related: '__mfield_partner.__mfield_model',
        }),
        __mfield_partnerName: attr({
            related: '__mfield_partner.__mfield_name',
        }),
        __mfield_resModel: attr({
            compute: '_computeResModel',
            default: '',
            dependencies: [
                '__mfield_channelModel',
                '__mfield_partnerModel',
            ],
        }),
        __mfield_selectedSubtypes: many2many('mail.follower_subtype'),
        __mfield_subtypes: many2many('mail.follower_subtype'),
    };

    Follower.modelName = 'mail.follower';

    return Follower;
}

registerNewModel('mail.follower', factory);

});
