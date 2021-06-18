/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one } from '@mail/model/model_field';
import { clear, insert, unlink, unlinkAll } from '@mail/model/model_field_command';

function factory(dependencies) {

    class Activity extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onAttachmentCreated = this.onAttachmentCreated.bind(this);
            this.onBlur = this.onBlur.bind(this);
            this.onClickActivity = this.onClickActivity.bind(this);
            this.onClickCancel = this.onClickCancel.bind(this);
            this.onClickDetailsButton = this.onClickDetailsButton.bind(this);
            this.onClickDiscard = this.onClickDiscard.bind(this);
            this.onClickDone = this.onClickDone.bind(this);
            this.onClickDoneAndScheduleNext = this.onClickDoneAndScheduleNext.bind(this);
            this.onClickEdit = this.onClickEdit.bind(this);
            this.onClickUploadDocument = this.onClickUploadDocument.bind(this);
            this.onKeydown = this.onKeydown.bind(this);
        }

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
                    data2.type = unlinkAll();
                } else {
                    data2.type = insert({
                        displayName: data.activity_type_id[1],
                        id: data.activity_type_id[0],
                    });
                }
            }
            if ('create_uid' in data) {
                if (!data.create_uid) {
                    data2.creator = unlinkAll();
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
            if ('res_id' in data && 'res_model' in data) {
                data2.thread = insert({
                    id: data.res_id,
                    model: data.res_model,
                });
            }
            if ('user_id' in data) {
                if (!data.user_id) {
                    data2.assignee = unlinkAll();
                } else {
                    data2.assignee = insert({
                        id: data.user_id[0],
                        display_name: data.user_id[1],
                    });
                }
            }
            if ('request_partner_id' in data) {
                if (!data.request_partner_id) {
                    data2.requestingPartner = unlink();
                } else {
                    data2.requestingPartner = insert({
                        id: data.request_partner_id[0],
                        display_name: data.request_partner_id[1],
                    });
                }
            }

            return data2;
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

        /**
         * Handles event on attachment creation by the file uploader.
         *
         * @param {CustomEvent} ev
         * @param {Object} ev.detail
         * @param {mail.attachment} ev.detail.attachment
         */
        onAttachmentCreated(ev) {
            this.markAsDone({ attachments: [ev.detail.attachment] });
        }

        /**
         * Handles click on the done bottom of the attachment popover.
         */
        async onClickDone() {
            await this.markAsDone({
                feedback: this.feedbackTextareaRef.el.value,
            });
            this.componentPopOver.trigger('reload', { keepChanges: true });
        }

        /**
         * Handles click on the Done and Schedule next button og the attachment popover.
         */
        onClickDoneAndScheduleNext() {
            this.markAsDoneAndScheduleNext({
                feedback: this.feedbackTextareaRef.el.value,
            });
        }

        /**
         * Handles blur event on the feedback textarea.
         */
        onBlur() {
            this.update({
                feedbackBackup: this.feedbackTextareaRef.el.value,
            });
        }

        /**
         * Handle click on activity component.
         *
         * @param {MouseEvent} ev
         */
        onClickActivity(ev) {
            if (
                ev.target.tagName === 'A' &&
                ev.target.dataset.oeId &&
                ev.target.dataset.oeModel
            ) {
                this.messaging.openProfile({
                    id: Number(ev.target.dataset.oeId),
                    model: ev.target.dataset.oeModel,
                });
                // avoid following dummy href
                ev.preventDefault();
            }
        }

        /**
         * @param {MouseEvent} ev
         */
        async onClickCancel(ev) {
            ev.preventDefault();
            await this.deleteServerRecord();
            this.component.trigger('reload', { keepChanges: true });
        }

        /**
         * Handle click on activity detail button.
         */
        onClickDetailsButton() {
            this.update({ areDetailsVisible: !this.areDetailsVisible });
        }

        /**
         * Handle click on activity edit button.
         */
        onClickEdit() {
            /**
             * Opens (legacy) form view dialog to edit current activity and updates
             * the activity when dialog is closed.
             */
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

        /**
         * @param {MouseEvent} ev
         */
        onClickUploadDocument(ev) {
            this.fileUploaderRef.comp.openBrowserFileUploader();
        }

        /**
         * Handles onKeydown event.
         */
        onKeydown(ev) {
            if (ev.key === 'Escape') {
                this._closePopOver();
            }
        }

        /**
         * Handles click on the discard button for the popover.
         */
        onClickDiscard() {
            this._closePopOver();
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _closePopOver() {
            this.componentPopOver.trigger('o-popover-close');
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentPartnerAssignee() {
            if (!this.assignee || !this.assignee.partner || !this.messaging.currentPartner) {
                return false;
            }
            return this.assignee.partner === this.messaging.currentPartner;
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
        /**
         * Determines if the detail box is visible.
         */
        areDetailsVisible: attr({
            default: false,
        }),
        assignee: many2one('mail.user'),
        attachments: many2many('mail.attachment', {
            inverse: 'activities',
        }),
        canWrite: attr({
            default: false,
        }),
        category: attr(),
        creator: many2one('mail.user'),
        /**
         * States the OWL component of this acivity.
         */
        component: attr(),
        /**
         * States the OWL component of this acivity popover.
         */
        componentPopOver: attr(),
        dateCreate: attr(),
        dateDeadline: attr(),
        /**
         * Backup of the feedback content of an activity to be marked as done in the popover.
         * Feature-specific to restoring the feedback content when component is re-mounted.
         * In all other cases, this field value should not be trusted.
         */
        feedbackBackup: attr(),
        /**
         * States the OWL ref of the "feedbackTextarea" of this activity popover.
         */
        feedbackTextareaRef: attr(),
        /**
         * States the OWL ref of the "fileUpload" of this activity.
         */
        fileUploaderRef: attr(),
        chaining_type: attr({
            default: 'suggest',
        }),
        icon: attr(),
        id: attr({
            readonly: true,
            required: true,
        }),
        isCurrentPartnerAssignee: attr({
            compute: '_computeIsCurrentPartnerAssignee',
            default: false,
        }),
        mailTemplates: many2many('mail.mail_template', {
            inverse: 'activities',
        }),
        /**
         * This value is meant to be returned by the server
         * (and has been sanitized before stored into db).
         * Do not use this value in a 't-raw' if the activity has been created
         * directly from user input and not from server data as it's not escaped.
         */
        note: attr({
            compute: '_computeNote',
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
    Activity.identifyingFields = ['id'];
    Activity.modelName = 'mail.activity';

    return Activity;
}

registerNewModel('mail.activity', factory);
