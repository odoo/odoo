/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insert } from '@mail/model/model_field_command';

const { markup } = owl;

registerModel({
    name: 'Activity',
    identifyingFields: ['Activity/id'],
    modelMethods: {
        /**
         * @param {Object} data
         * @return {Object}
         */
        convertData(data) {
            const data2 = {};
            if ('activity_category' in data) {
                data2['Activity/category'] = data.activity_category;
            }
            if ('can_write' in data) {
                data2['Activity/canWrite'] = data.can_write;
            }
            if ('create_date' in data) {
                data2['Activity/dateCreate'] = data.create_date;
            }
            if ('date_deadline' in data) {
                data2['Activity/dateDeadline'] = data.date_deadline;
            }
            if ('chaining_type' in data) {
                data2['Activity/chaining_type'] = data.chaining_type;
            }
            if ('icon' in data) {
                data2['Activity/icon'] = data.icon;
            }
            if ('id' in data) {
                data2['Activity/id'] = data.id;
            }
            if ('note' in data) {
                data2['Activity/note'] = data.note;
            }
            if ('state' in data) {
                data2['Activity/state'] = data.state;
            }
            if ('summary' in data) {
                data2['Activity/summary'] = data.summary;
            }

            // relation
            if ('activity_type_id' in data) {
                if (!data.activity_type_id) {
                    data2['Activity/type'] = clear();
                } else {
                    data2['Activity/type'] = insert({
                        'ActivityType/displayName': data.activity_type_id[1],
                        'ActivityType/id': data.activity_type_id[0],
                    });
                }
            }
            if ('create_uid' in data) {
                if (!data.create_uid) {
                    data2['Activity/creator'] = clear();
                } else {
                    data2['Activity/creator'] = insert({
                        'User/id': data.create_uid[0],
                        'User/display_name': data.create_uid[1],
                    });
                }
            }
            if ('mail_template_ids' in data) {
                data2['Activity/mailTemplates'] = insert(data.mail_template_ids);
            }
            if ('res_id' in data && 'res_model' in data) {
                data2['Activity/thread'] = insert({
                    'Thread/id': data.res_id,
                    'Thread/model': data.res_model,
                });
            }
            if ('user_id' in data) {
                if (!data.user_id) {
                    data2['Activity/assignee'] = clear();
                } else {
                    data2['Activity/assignee'] = insert({
                        'User/id': data.user_id[0],
                        'User/display_name': data.user_id[1],
                    });
                }
            }
            if ('request_partner_id' in data) {
                if (!data.request_partner_id) {
                    data2['Activity/requestingPartner'] = clear();
                } else {
                    data2['Activity/requestingPartner'] = insert({
                        'Partner/id': data.request_partner_id[0],
                        'Partner/display_name': data.request_partner_id[1],
                    });
                }
            }

            return data2;
        },
    },
    recordMethods: {
        /**
         * Delete the record from database and locally.
         */
        async deleteServerRecord() {
            await this.async(() => this['Record/messaging'].rpc({
                model: 'mail.activity',
                method: 'unlink',
                args: [[this['Activity/id']]],
            }));
            this.delete();
        },
        /**
         * Opens (legacy) form view dialog to edit current activity and updates
         * the activity when dialog is closed.
         */
        edit() {
            const action = {
                type: 'ir.actions.act_window',
                name: this.env._t("Schedule Activity"),
                res_model: 'mail.activity',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_res_id: this['Activity/thread']['Thread/id'],
                    default_res_model: this['Activity/thread']['Thread/model'],
                },
                res_id: this['Activity/id'],
            };
            this.env.bus.trigger('do-action', {
                action,
                options: { on_close: () => this.fetchAndUpdate() },
            });
        },
        async fetchAndUpdate() {
            const [data] = await this['Record/messaging'].rpc({
                model: 'mail.activity',
                method: 'activity_format',
                args: [this['Activity/id']],
            }, { shadow: true }).catch(e => {
                const errorName = e.message && e.message.data && e.message.data.name;
                if (errorName === 'odoo.exceptions.MissingError') {
                    return [];
                } else {
                    throw e;
                }
            });
            let shouldDelete = false;
            if (data) {
                this.update(this.constructor.convertData(data));
            } else {
                shouldDelete = true;
            }
            this['Activity/thread'].fetchData(['activities', 'attachments', 'messages']);
            if (shouldDelete) {
                this.delete();
            }
        },
        /**
         * @param {Object} param0
         * @param {Attachment[]} [param0.attachments=[]]
         * @param {string|boolean} [param0.feedback=false]
         */
        async markAsDone({ attachments = [], feedback = false }) {
            const attachmentIds = attachments.map(attachment => attachment['Attachment.id']);
            await this.async(() => this['Record/messaging'].rpc({
                model: 'mail.activity',
                method: 'action_feedback',
                args: [[this['Activity/id']]],
                kwargs: {
                    attachment_ids: attachmentIds,
                    feedback,
                },
            }));
            this['Activity/thread'].fetchData(['attachments', 'messages']);
            this.delete();
        },
        /**
         * @param {Object} param0
         * @param {string} param0.feedback
         * @returns {Object}
         */
        async markAsDoneAndScheduleNext({ feedback }) {
            const action = await this.async(() => this['Record/messaging'].rpc({
                model: 'mail.activity',
                method: 'action_feedback_schedule_next',
                args: [[this['Activity/id']]],
                kwargs: { feedback },
            }));
            this['Activity/thread'].fetchData(['activities', 'attachments', 'messages']);
            const thread = this['Activity/thread'];
            this.delete();
            if (!action) {
                return;
            }
            this.env.bus.trigger('do-action', {
                action,
                options: {
                    on_close: () => {
                        thread.fetchData(['activities']);
                    },
                },
            });
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentPartnerAssignee() {
            if (
                !this['Activity/assignee'] ||
                !this['Activity/assignee']['User/partner'] ||
                !this['Record/messaging']['Messaging/currentPartner']
            ) {
                return false;
            }
            return this['Activity/assignee']['User/partner'] === this['Record/messaging']['Messaging/currentPartner'];
        },
        /**
         * Wysiwyg editor put `<p><br></p>` even without a note on the activity.
         * This compute replaces this almost empty value by an actual empty
         * value, to reduce the size the empty note takes on the UI.
         *
         * @private
         * @returns {string|undefined}
         */
        _computeNote() {
            if (this['Activity/note'] === '<p><br></p>') {
                return clear();
            }
            return this['Activity/note'];
        },
        /**
         * @private
         * @returns {Markup}
         */
        _computeNoteAsMarkup() {
            return markup(this['Activity/note']);
        },
    },
    fields: {
        'Activity/activityViews': many('ActivityView', {
            inverse: 'ActivityView/activity',
            isCausal: true,
        }),
        'Activity/assignee': one('User'),
        'Activity/attachments': many('Attachment', {
            inverse: 'activities',
        }),
        'Activity/canWrite': attr({
            default: false,
        }),
        'Activity/category': attr(),
        'Activity/creator': one('User'),
        'Activity/dateCreate': attr(),
        'Activity/dateDeadline': attr(),
        /**
         * Backup of the feedback content of an activity to be marked as done in the popover.
         * Feature-specific to restoring the feedback content when component is re-mounted.
         * In all other cases, this field value should not be trusted.
         */
        'Activity/feedbackBackup': attr(),
        'Activity/chaining_type': attr({
            default: 'suggest',
        }),
        'Activity/icon': attr(),
        'Activity/id': attr({
            readonly: true,
            required: true,
        }),
        'Activity/isCurrentPartnerAssignee': attr({
            compute: '_computeIsCurrentPartnerAssignee',
            default: false,
        }),
        'Activity/mailTemplates': many('MailTemplate', {
            inverse: 'MailTemplate/activities',
        }),
        /**
         * This value is meant to be returned by the server
         * (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the activity has been created
         * directly from user input and not from server data as it's not escaped.
         */
        'Activity/note': attr({
            compute: '_computeNote',
        }),
        'Activity/noteAsMarkup': attr({
            compute: '_computeNoteAsMarkup',
        }),
        /**
         * Determines that an activity is linked to a requesting partner or not.
         * It will be used notably in website slides to know who triggered the
         * "request access" activity.
         * Also, be useful when the assigned user is different from the
         * "source" or "requesting" partner.
         */
        'Activity/requestingPartner': one('Partner'),
        'Activity/state': attr(),
        'Activity/summary': attr(),
        /**
         * Determines to which "thread" (using `mail.activity.mixin` on the
         * server) `this` belongs to.
         */
        'Activity/thread': one('Thread', {
            inverse: 'Thread/activities',
        }),
        'Activity/type': one('ActivityType', {
            inverse: 'ActivityType/activities',
        }),
    },
});
