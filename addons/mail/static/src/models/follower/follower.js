/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2many } from '@mail/model/model_field';
import { clear, insert, insertAndReplace, link, replace, unlink, unlinkAll } from '@mail/model/model_field_command';

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
                        display_name: data.display_name,
                        email: data.email,
                        id: data.partner_id,
                        name: data.name,
                    };
                    data2.partner = insert(partnerData);
                }
            }
            if (data.partner) {
                data2.partner = insertAndReplace(this.models['mail.partner'].convertData(data.partner));
            }
            return data2;
        }

        /**
         *  Close subtypes dialog
         */
        closeSubtypes() {
            this.update({ subtypeList: clear() });
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
                const subtype = this.messaging.models['mail.follower_subtype'].insert(
                    this.messaging.models['mail.follower_subtype'].convertData(data)
                );
                this.update({ subtypes: link(subtype) });
                if (data.followed) {
                    this.update({ selectedSubtypes: link(subtype) });
                } else {
                    this.update({ selectedSubtypes: unlink(subtype) });
                }
            }
            this.messaging.dialogManager.update({
                dialogs: insert({
                    followerSubtypeList: insertAndReplace({
                        follower: replace(this),
                    }),
                }),
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

    }

    Follower.fields = {
        followedThread: many2one('mail.thread', {
            inverse: 'followers',
        }),
        id: attr({
            readonly: true,
            required: true,
        }),
        isActive: attr({
            default: true,
        }),
        isEditable: attr({
            default: false,
        }),
        partner: many2one('mail.partner', {
            required: true,
        }),
        selectedSubtypes: many2many('mail.follower_subtype'),
        subtypeList: one2many('mail.follower_subtype_list', {
            inverse: 'follower',
            isCausal: true,
        }),
        subtypes: many2many('mail.follower_subtype'),
    };
    Follower.identifyingFields = ['id'];
    Follower.modelName = 'mail.follower';

    return Follower;
}

registerNewModel('mail.follower', factory);
