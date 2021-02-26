odoo.define('mail/static/src/models/follower.follower.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one } = require('mail/static/src/model/model_field.js');
const { insert, link, unlink, unlinkAll } = require('mail/static/src/model/model_field_command.js');

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
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('is_active' in data) {
                data2.isActive = data.is_active;
            }
            if ('is_editable' in data) {
                data2.isEditable = data.is_editable;
            }
            if ('partner_id' in data) {
                if (!data.partner_id) {
                    data2.partner = unlinkAll();
                } else {
                    const partnerData = {
                        email: data.email,
                        id: data.partner_id,
                        name: data.name,
                    };
                    data2.partner = insert(partnerData);
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
            return this.partner.openProfile();
        }

        /**
         * Remove this follower from its related thread.
         */
        async remove() {
            const partner_ids = [];
            partner_ids.push(this.partner.id);
            await this.async(() => this.env.services.rpc({
                model: this.followedThread.model,
                method: 'message_unsubscribe',
                args: [[this.followedThread.id], partner_ids]
            }));
            const followedThread = this.followedThread;
            this.delete();
            followedThread.fetchAndUpdateSuggestedRecipients();
        }

        /**
         * @param {mail.follower_subtype} subtype
         */
        selectSubtype(subtype) {
            if (!this.selectedSubtypes.includes(subtype)) {
                this.update({ selectedSubtypes: link(subtype) });
            }
        }

        /**
         * Show (editable) list of subtypes of this follower.
         */
        async showSubtypes() {
            const subtypesData = await this.async(() => this.env.services.rpc({
                route: '/mail/read_subscription_data',
                params: { follower_id: this.id },
            }));
            this.update({ subtypes: unlinkAll() });
            for (const data of subtypesData) {
                const subtype = this.env.models['mail.follower_subtype'].insert(
                    this.env.models['mail.follower_subtype'].convertData(data)
                );
                this.update({ subtypes: link(subtype) });
                if (data.followed) {
                    this.update({ selectedSubtypes: link(subtype) });
                } else {
                    this.update({ selectedSubtypes: unlink(subtype) });
                }
            }
            this._subtypesListDialog = this.env.messaging.dialogManager.open('mail.follower_subtype_list', {
                follower: link(this),
            });
        }

        /**
         * @param {mail.follower_subtype} subtype
         */
        unselectSubtype(subtype) {
            if (this.selectedSubtypes.includes(subtype)) {
                this.update({ selectedSubtypes: unlink(subtype) });
            }
        }

        /**
         * Update server-side subscription of subtypes of this follower.
         */
        async updateSubtypes() {
            if (this.selectedSubtypes.length === 0) {
                this.remove();
            } else {
                const kwargs = {
                    subtype_ids: this.selectedSubtypes.map(subtype => subtype.id),
                };
                if (this.partner) {
                    kwargs.partner_ids = [this.partner.id];
                }
                await this.async(() => this.env.services.rpc({
                    model: this.followedThread.model,
                    method: 'message_subscribe',
                    args: [[this.followedThread.id]],
                    kwargs,
                }));
                this.env.services['notification'].notify({
                    type: 'success',
                    message: this.env._t("The subscription preferences were successfully applied."),
                });
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
            return `${this.modelName}_${data.id}`;
        }

    }

    Follower.fields = {
        followedThread: many2one('mail.thread', {
            inverse: 'followers',
        }),
        id: attr({
            required: true,
        }),
        isActive: attr({
            default: true,
        }),
        isEditable: attr({
            default: false,
        }),
        name: attr({
            related: 'partner.name',
        }),
        partner: many2one('mail.partner', {
            required: true,
        }),
        partnerId: attr({
            related: 'partner.id',
        }),
        selectedSubtypes: many2many('mail.follower_subtype'),
        subtypes: many2many('mail.follower_subtype'),
    };

    Follower.modelName = 'mail.follower';

    return Follower;
}

registerNewModel('mail.follower', factory);

});
