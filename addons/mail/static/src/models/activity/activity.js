odoo.define('mail/static/src/models/activity/activity/js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { clear } = require('mail/static/src/model/model_field_command.js');
const { attr, many2many, many2one } = require('mail/static/src/model/model_field_utils.js');

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
                args: [[this.__mfield_id()]],
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
                data2.__mfield_category = data.activity_category;
            }
            if ('can_write' in data) {
                data2.__mfield_canWrite = data.can_write;
            }
            if ('create_data' in data) {
                data2.__mfield_dateCreate = data.create_date;
            }
            if ('date_deadline' in data) {
                data2.__mfield_dateDeadline = data.date_deadline;
            }
            if ('force_next' in data) {
                data2.__mfield_force_next = data.force_next;
            }
            if ('icon' in data) {
                data2.__mfield_icon = data.icon;
            }
            if ('id' in data) {
                data2.__mfield_id = data.id;
            }
            if ('note' in data) {
                data2.__mfield_note = data.note;
            }
            if ('res_id' in data) {
                data2.__mfield_res_id = data.res_id;
            }
            if ('res_model' in data) {
                data2.__mfield_res_model = data.res_model;
            }
            if ('state' in data) {
                data2.__mfield_state = data.state;
            }
            if ('summary' in data) {
                data2.__mfield_summary = data.summary;
            }

            // relation
            if ('activity_type_id' in data) {
                if (!data.activity_type_id) {
                    data2.__mfield_type = [['unlink-all']];
                } else {
                    data2.__mfield_type = [
                        ['insert', {
                            __mfield_displayName: data.activity_type_id[1],
                            __mfield_id: data.activity_type_id[0],
                        }],
                    ];
                }
            }
            if ('create_uid' in data) {
                if (!data.create_uid) {
                    data2.__mfield_creator = [['unlink-all']];
                } else {
                    data2.creator = [
                        ['insert', {
                            __mfield_id: data.create_uid[0],
                            __mfield_display_name: data.create_uid[1],
                        }],
                    ];
                }
            }
            if ('mail_template_ids' in data) {
                data2.__mfield_mailTemplates = [['insert', {
                    __mfield_id: data.mail_template_ids.id,
                    __mfield_name: data.mail_template_ids.name,
                }]];
            }
            if ('user_id' in data) {
                if (!data.user_id) {
                    data2.__mfield_assignee = [['unlink-all']];
                } else {
                    data2.__mfield_assignee = [
                        ['insert', {
                            __mfield_id: data.user_id[0],
                            __mfield_display_name: data.user_id[1],
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
                    default_res_id: this.__mfield_res_id(this),
                    default_res_model: this.__mfield_res_model(this),
                },
                res_id: this.__mfield_id(this),
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
                args: [this.__mfield_id(this)],
            }));
            this.update(this.constructor.convertData(data));
            if (this.__mfield_chatter(this)) {
                this.__mfield_chatter(this).refresh();
            }
        }

        /**
         * @param {Object} param0
         * @param {mail.attachment[]} [param0.attachments=[]]
         * @param {string|boolean} [param0.feedback=false]
         */
        async markAsDone({ attachments = [], feedback = false }) {
            const attachmentIds = attachments.map(attachment => attachment.__mfield_id(this));
            await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'action_feedback',
                args: [[this.__mfield_id(this)]],
                kwargs: {
                    attachment_ids: attachmentIds,
                    feedback,
                },
                context: this.__mfield_chatter(this) ? this.__mfield_chatter(this).__mfield_context(this) : {},
            }));
            if (this.__mfield_chatter(this)) {
                this.__mfield_chatter(this).refresh();
            }
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
                args: [[this.__mfield_id(this)]],
                kwargs: { feedback },
            }));
            const chatter = this.__mfield_chatter(this);
            if (chatter) {
                this.__mfield_chatter(this).refresh();
            }
            this.delete();
            this.env.bus.trigger('do-action', {
                action,
                options: {
                    on_close: () => {
                        if (chatter) {
                            chatter.refreshActivities();
                        }
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
            return `${this.modelName}_${data.__mfield_id}`;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentPartnerAssignee() {
            if (
                !this.__mfield_assigneePartner(this) ||
                !this.__mfield_messagingCurrentPartner(this)
            ) {
                return false;
            }
            return this.__mfield_assigneePartner(this) === this.__mfield_messagingCurrentPartner(this);
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
            if (this.__mfield_note(this) === '<p><br></p>') {
                return clear();
            }
            return this.__mfield_note(this);
        }
    }

    Activity.fields = {
        __mfield_assignee: many2one('mail.user'),
        __mfield_assigneePartner: many2one('mail.partner', {
            related: '__mfield_assignee.__mfield_partner',
        }),
        __mfield_attachments: many2many('mail.attachment', {
            inverse: '__mfield_activities',
        }),
        __mfield_canWrite: attr({
            default: false,
        }),
        __mfield_category: attr(),
        __mfield_chatter: many2one('mail.chatter', {
            inverse: '__mfield_activities',
        }),
        __mfield_creator: many2one('mail.user'),
        __mfield_dateCreate: attr(),
        __mfield_dateDeadline: attr(),
        __mfield_force_next: attr({
            default: false,
        }),
        __mfield_icon: attr(),
        __mfield_id: attr(),
        __mfield_isCurrentPartnerAssignee: attr({
            compute: '_computeIsCurrentPartnerAssignee',
            default: false,
            dependencies: [
                '__mfield_assigneePartner',
                '__mfield_messagingCurrentPartner',
            ],
        }),
        __mfield_mailTemplates: many2many('mail.mail_template', {
            inverse: '__mfield_activities',
        }),
        __mfield_messaging: many2one('mail.messaging', {
            compute: '_computeMessaging',
        }),
        __mfield_messagingCurrentPartner: many2one('mail.partner', {
            related: '__mfield_messaging.__mfield_currentPartner',
        }),
        /**
         * This value is meant to be returned by the server
         * (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the activity has been created
         * directly from user input and not from server data as it's not escaped.
         */
        __mfield_note: attr({
            compute: '_computeNote',
            dependencies: [
                '__mfield_note',
            ],
        }),
        __mfield_res_id: attr(),
        __mfield_res_model: attr(),
        __mfield_state: attr(),
        __mfield_summary: attr(),
        __mfield_type: many2one('mail.activity_type', {
            inverse: '__mfield_activities',
        }),
    };

    Activity.modelName = 'mail.activity';

    return Activity;
}

registerNewModel('mail.activity', factory);

});
