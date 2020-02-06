odoo.define('mail.messaging.entity.Activity', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

function ActivityFactory({ Entity }) {

    class Activity extends Entity {

        /**
         * @override
         */
        delete() {
            this.env.rpc({
                model: 'mail.activity',
                method: 'unlink',
                args: [[this.id]],
            });
            super.delete();
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        async fetchAndUpdate() {
            const data = await this.env.rpc({
                model: 'mail.activity',
                method: 'activity_format',
                args: [this.id],
            });
            this.update(data);
            if (this.chatter) {
                this.chatter.refresh();
            }
        }

        /**
         * @param {Object} param0
         * @param {mail.messaging.entity.Attachment[]} param0.attachments
         * @param {string|boolean} [param0.feedback=false]
         */
        async markAsDone({ attachments, feedback = false }) {
            const attachmentIds = attachments.map(attachment => attachment.id);
            await this.env.rpc({
                model: 'mail.activity',
                method: 'action_feedback',
                args: [[this.id]],
                kwargs: {
                    attachment_ids: attachmentIds,
                    context: this.chatter.context,
                    feedback,
                },
            });
            this.chatter.refresh();
            this.delete();
        }

        /**
         * @param {Object} param0
         * @param {string} param0.feedback
         * @returns {Object}
         */
        async markAsDoneAndSchedule({ feedback }) {
            const action = await this.env.rpc({
                model: 'mail.activity',
                method: 'action_feedback_schedule_next',
                args: [[this.id]],
                kwargs: { feedback },
            });
            this.chatter.refresh();
            this.delete();
            return action;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _update(data) {
            let {
                activity_category: category,
                activity_type_id: [
                    activityTypeId,
                    activityTypeDisplayName,
                ] = [],
                can_write: canWrite,
                create_date: dateCreate,
                create_uid: [
                    creatorId,
                    creatorDisplayName,
                ] = [],
                date_deadline: dateDeadline,
                forceNext = this.forceNext || false,
                icon,
                id = this.id,
                mail_template_ids = [],
                note,
                res_id = this.res_id,
                res_model: res_model = this.res_model,
                state,
                summary,
                user_id: [
                    assigneeId,
                    assigneeDisplayName,
                ] = [],
            } = data;

            this._write({
                canWrite,
                category,
                dateCreate,
                dateDeadline,
                forceNext,
                icon,
                id,
                note,
                res_id,
                res_model,
                state,
                summary,
            });

            // activity_type
            if (activityTypeId) {
                const type = this.env.entities.ActivityType.insert({
                    displayName: activityTypeDisplayName,
                    id: activityTypeId,
                });
                this.link({ type });
            }
            // assignee
            if (assigneeId) {
                const assignee = this.env.entities.User.insert({
                    displayName: assigneeDisplayName,
                    id: assigneeId,
                });
                this.link({ assignee });
            }
            // creator
            if (creatorId) {
                const creator = this.env.entities.User.insert({
                    displayName: creatorDisplayName,
                    id: creatorId,
                });
                this.link({ creator });
            }
            // mail templates
            for (const mailTemplateData of mail_template_ids) {
                const mailTemplate = this.env.entities.MailTemplate.insert(mailTemplateData);
                this.link({ mailTemplates: mailTemplate });
            }
        }

    }

    Object.assign(Activity, {
        relations: Object.assign({}, Entity.relations, {
            assignee: {
                inverse: 'activitiesAsAssignee',
                to: 'User',
                type: 'many2one',
            },
            attachments: {
                inverse: 'activities',
                to: 'Attachment',
                type: 'many2many',
            },
            chatter: {
                inverse: 'activities',
                to: 'Chatter',
                type: 'many2one'
            },
            creator: {
                inverse: 'activitiesAsCreator',
                to: 'User',
                type: 'many2one',
            },
            mailTemplates: {
                inverse: 'activities',
                to: 'MailTemplate',
                type: 'many2many',
            },
            type: {
                inverse: 'activities',
                to: 'ActivityType',
                type: 'many2one',
            },
        }),
    });

    return Activity;
}

registerNewEntity('Activity', ActivityFactory);

});
