/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insert } from '@mail/model/model_field_command';

const { markup } = owl;

registerModel({
    name: 'Activity',
    modelMethods: {
        /**
         * @param {Object} data
         * @return {Object}
         */
        convertData(data) {
            const data2 = {};
            if ('activity_category' in data) {
                data2.category = data.activity_category;
            }
            if ('can_write' in data) {
                data2.canWrite = data.can_write;
            }
            if ('create_date' in data) {
                data2.dateCreate = data.create_date;
            }
            if ('date_deadline' in data) {
                data2.dateDeadline = data.date_deadline;
            }
            if ('chaining_type' in data) {
                data2.chaining_type = data.chaining_type;
            }
            if ('icon' in data) {
                data2.icon = data.icon;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('note' in data) {
                data2.rawNote = data.note;
            }
            if ('state' in data) {
                data2.state = data.state;
            }
            if ('summary' in data) {
                data2.summary = data.summary;
            }

            // relation
            if ('activity_type_id' in data) {
                if (!data.activity_type_id) {
                    data2.type = clear();
                } else {
                    data2.type = insert({
                        displayName: data.activity_type_id[1],
                        id: data.activity_type_id[0],
                    });
                }
            }
            if ('create_uid' in data) {
                if (!data.create_uid) {
                    data2.creator = clear();
                } else {
                    data2.creator = insert({
                        id: data.create_uid[0],
                        display_name: data.create_uid[1],
                    });
                }
            }
            if ('mail_template_ids' in data) {
                data2.mailTemplates = insert(data.mail_template_ids);
            }
            if (data.res_id && data.res_model) {
                data2.thread = insert({
                    id: data.res_id,
                    model: data.res_model,
                });
            }
            if ('user_id' in data) {
                if (!data.user_id) {
                    data2.assignee = clear();
                } else {
                    data2.assignee = insert({
                        id: data.user_id[0],
                        display_name: data.user_id[1],
                    });
                }
            }
            if ('request_partner_id' in data) {
                if (!data.request_partner_id) {
                    data2.requestingPartner = clear();
                } else {
                    data2.requestingPartner = insert({
                        id: data.request_partner_id[0],
                        display_name: data.request_partner_id[1],
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
            await this.messaging.rpc({
                model: 'mail.activity',
                method: 'unlink',
                args: [[this.id]],
            });
            if (!this.exists()) {
                return;
            }
            this.delete();
        },
        /**
         * Opens (legacy) form view dialog to edit current activity and updates
         * the activity when dialog is closed.
         *
         * @return {Promise} promise that is fulfilled when the form has been closed
         */
        async edit() {
            await this.messaging.openActivityForm({ activity: this });
            if (this.exists()) {
                this.fetchAndUpdate();
            }
        },
        async fetchAndUpdate() {
            const [data] = await this.messaging.rpc({
                model: 'mail.activity',
                method: 'activity_format',
                args: [this.id],
            }, { shadow: true }).catch(e => {
                const errorName = e.message && e.message.data && e.message.data.name;
                if ([errorName, e.exceptionName].includes('odoo.exceptions.MissingError')) {
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
            this.thread.fetchData(['activities', 'attachments', 'messages']);
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
            const attachmentIds = attachments.map(attachment => attachment.id);
            const thread = this.thread;
            await this.messaging.rpc({
                model: 'mail.activity',
                method: 'action_feedback',
                args: [[this.id]],
                kwargs: {
                    attachment_ids: attachmentIds,
                    feedback,
                },
            });
            if (thread.exists()) {
                thread.fetchData(['attachments', 'messages']);
            }
            if (!this.exists()) {
                return;
            }
            this.delete();
        },
        /**
         * @param {Object} param0
         * @param {string} param0.feedback
         * @returns {Object}
         */
        async markAsDoneAndScheduleNext({ feedback }) {
            const thread = this.thread;
            const action = await this.messaging.rpc({
                model: 'mail.activity',
                method: 'action_feedback_schedule_next',
                args: [[this.id]],
                kwargs: { feedback },
            });
            if (thread.exists()) {
                thread.fetchData(['activities', 'attachments', 'messages']);
            }
            if (this.exists()) {
                this.delete();
            }
            if (!action) {
                return;
            }
            await new Promise(resolve => {
                this.env.services.action.doAction(
                    action,
                    {
                        onClose: resolve,
                    },
                );
            });
            if (!thread.exists()) {
                return;
            }
            thread.fetchData(['activities']);
        },
    },
    fields: {
        activityViews: many('ActivityView', {
            inverse: 'activity',
        }),
        assignee: one('User', {
            inverse: 'activitiesAsAssignee',
        }),
        attachments: many('Attachment', {
            inverse: 'activities',
        }),
        canWrite: attr({
            default: false,
        }),
        category: attr(),
        creator: one('User'),
        dateCreate: attr(),
        dateDeadline: attr(),
        /**
         * Backup of the feedback content of an activity to be marked as done in the popover.
         * Feature-specific to restoring the feedback content when component is re-mounted.
         * In all other cases, this field value should not be trusted.
         */
        feedbackBackup: attr(),
        chaining_type: attr({
            default: 'suggest',
        }),
        icon: attr(),
        id: attr({
            identifying: true,
        }),
        isCurrentPartnerAssignee: attr({
            compute() {
                if (!this.assignee || !this.assignee.partner || !this.messaging.currentPartner) {
                    return false;
                }
                return this.assignee.partner === this.messaging.currentPartner;
            },
            default: false,
        }),
        mailTemplates: many('MailTemplate', {
            inverse: 'activities',
        }),
        /**
         * This value is meant to be returned by the server
         * (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the activity has been created
         * directly from user input and not from server data as it's not escaped.
         */
        note: attr({
            /**
             * Wysiwyg editor put `<p><br></p>` even without a note on the activity.
             * This compute replaces this almost empty value by an actual empty
             * value, to reduce the size the empty note takes on the UI.
             */
            compute() {
                if (this.rawNote === '<p><br></p>') {
                    return clear();
                }
                return this.rawNote;
            },
        }),
        noteAsMarkup: attr({
            compute() {
                return markup(this.note);
            },
        }),
        rawNote: attr(),
        /**
         * Determines that an activity is linked to a requesting partner or not.
         * It will be used notably in website slides to know who triggered the
         * "request access" activity.
         * Also, be useful when the assigned user is different from the
         * "source" or "requesting" partner.
         */
        requestingPartner: one('Partner'),
        state: attr(),
        summary: attr(),
        /**
         * Determines to which "thread" (using `mail.activity.mixin` on the
         * server) `this` belongs to.
         */
        thread: one('Thread', {
            inverse: 'activities',
        }),
        type: one('ActivityType', {
            inverse: 'activities',
        }),
    },
});
