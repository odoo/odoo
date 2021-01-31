odoo.define('mail/static/src/models/activity/activity/js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one } = require('mail/static/src/model/model_field.js');
const { clear } = require('mail/static/src/model/model_field_command.js');

function factory(dependencies) {

    class Activity extends dependencies['mail.model'] {


        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Delete the record from database and locally.
         */
        async deleteServerRecord() {
            await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'unlink',
                args: [[this.id]],
            }));
            this.delete();
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} data
         * @return {Object}
         */
        static convertData(data) {
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
            if ('force_next' in data) {
                data2.force_next = data.force_next;
            }
            if ('icon' in data) {
                data2.icon = data.icon;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('note' in data) {
                data2.note = data.note;
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
                    data2.type = [['unlink-all']];
                } else {
                    data2.type = [
                        ['insert', {
                            displayName: data.activity_type_id[1],
                            id: data.activity_type_id[0],
                        }],
                    ];
                }
            }
            if ('create_uid' in data) {
                if (!data.create_uid) {
                    data2.creator = [['unlink-all']];
                } else {
                    data2.creator = [
                        ['insert', {
                            id: data.create_uid[0],
                            display_name: data.create_uid[1],
                        }],
                    ];
                }
            }
            if ('mail_template_ids' in data) {
                data2.mailTemplates = [['insert', data.mail_template_ids]];
            }
            if ('res_id' in data && 'res_model' in data) {
                data2.thread = [['insert', {
                    id: data.res_id,
                    model: data.res_model,
                }]];
            }
            if ('user_id' in data) {
                if (!data.user_id) {
                    data2.assignee = [['unlink-all']];
                } else {
                    data2.assignee = [
                        ['insert', {
                            id: data.user_id[0],
                            display_name: data.user_id[1],
                        }],
                    ];
                }
            }
            if ('request_partner_id' in data) {
                if (!data.request_partner_id) {
                    data2.requestingPartner = [['unlink']];
                } else {
                    data2.requestingPartner = [
                        ['insert', {
                            id: data.request_partner_id[0],
                            display_name: data.request_partner_id[1],
                        }],
                    ];
                }
            }

            return data2;
        }

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
                    default_res_id: this.thread.id,
                    default_res_model: this.thread.model,
                },
                res_id: this.id,
            };
            this.env.bus.trigger('do-action', {
                action,
                options: { on_close: () => this.fetchAndUpdate() },
            });
        }

        async fetchAndUpdate() {
            const [data] = await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'activity_format',
                args: [this.id],
            }, { shadow: true }));
            let shouldDelete = false;
            if (data) {
                this.update(this.constructor.convertData(data));
            } else {
                shouldDelete = true;
            }
            this.thread.refreshActivities();
            this.thread.refresh();
            if (shouldDelete) {
                this.delete();
            }
        }

        /**
         * @param {Object} param0
         * @param {mail.attachment[]} [param0.attachments=[]]
         * @param {string|boolean} [param0.feedback=false]
         */
        async markAsDone({ attachments = [], feedback = false }) {
            const attachmentIds = attachments.map(attachment => attachment.id);
            await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'action_feedback',
                args: [[this.id]],
                kwargs: {
                    attachment_ids: attachmentIds,
                    feedback,
                },
            }));
            this.thread.refresh();
            this.delete();
        }

        /**
         * @param {Object} param0
         * @param {string} param0.feedback
         * @returns {Object}
         */
        async markAsDoneAndScheduleNext({ feedback }) {
            const action = await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'action_feedback_schedule_next',
                args: [[this.id]],
                kwargs: { feedback },
            }));
            this.thread.refresh();
            const thread = this.thread;
            this.delete();
            if (!action) {
                thread.refreshActivities();
                return;
            }
            this.env.bus.trigger('do-action', {
                action,
                options: {
                    on_close: () => {
                        thread.refreshActivities();
                    },
                },
            });
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

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentPartnerAssignee() {
            if (!this.assigneePartner || !this.messagingCurrentPartner) {
                return false;
            }
            return this.assigneePartner === this.messagingCurrentPartner;
        }

        /**
         * @private
         * @returns {mail.messaging}
         */
        _computeMessaging() {
            return [['link', this.env.messaging]];
        }

        /**
         * Wysiwyg editor put `<p><br></p>` even without a note on the activity.
         * This compute replaces this almost empty value by an actual empty
         * value, to reduce the size the empty note takes on the UI.
         *
         * @private
         * @returns {string|undefined}
         */
        _computeNote() {
            if (this.note === '<p><br></p>') {
                return clear();
            }
            return this.note;
        }
    }

    Activity.fields = {
        assignee: many2one('mail.user'),
        assigneePartner: many2one('mail.partner', {
            related: 'assignee.partner',
        }),
        attachments: many2many('mail.attachment', {
            inverse: 'activities',
        }),
        canWrite: attr({
            default: false,
        }),
        category: attr(),
        creator: many2one('mail.user'),
        dateCreate: attr(),
        dateDeadline: attr(),
        /**
         * Backup of the feedback content of an activity to be marked as done in the popover.
         * Feature-specific to restoring the feedback content when component is re-mounted.
         * In all other cases, this field value should not be trusted.
         */
        feedbackBackup: attr(),
        force_next: attr({
            default: false,
        }),
        icon: attr(),
        id: attr(),
        isCurrentPartnerAssignee: attr({
            compute: '_computeIsCurrentPartnerAssignee',
            default: false,
            dependencies: [
                'assigneePartner',
                'messagingCurrentPartner',
            ],
        }),
        mailTemplates: many2many('mail.mail_template', {
            inverse: 'activities',
        }),
        messaging: many2one('mail.messaging', {
            compute: '_computeMessaging',
        }),
        messagingCurrentPartner: many2one('mail.partner', {
            related: 'messaging.currentPartner',
        }),
        /**
         * This value is meant to be returned by the server
         * (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the activity has been created
         * directly from user input and not from server data as it's not escaped.
         */
        note: attr({
            compute: '_computeNote',
            dependencies: [
                'note',
            ],
        }),
        /**
         * Determines that an activity is linked to a requesting partner or not.
         * It will be used notably in website slides to know who triggered the
         * "request access" activity.
         * Also, be useful when the assigned user is different from the
         * "source" or "requesting" partner.
         */
        requestingPartner: many2one('mail.partner'),
        state: attr(),
        summary: attr(),
        /**
         * Determines to which "thread" (using `mail.activity.mixin` on the
         * server) `this` belongs to.
         */
        thread: many2one('mail.thread', {
            inverse: 'activities',
        }),
        type: many2one('mail.activity_type', {
            inverse: 'activities',
        }),
    };

    Activity.modelName = 'mail.activity';

    return Activity;
}

registerNewModel('mail.activity', factory);

});
