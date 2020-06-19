odoo.define('mail/static/src/models/mail_template/mail_template.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class MailTemplate extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {mail.activity} activity
         */
        preview(activity) {
            const action = {
                name: this.env._t("Compose Email"),
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_res_id: activity.res_id,
                    default_model: activity.res_model,
                    default_use_template: true,
                    default_template_id: this.id,
                    force_email: true,
                },
            };
            this.env.bus.trigger('do-action', {
                action,
                options: {
                    on_close: () => {
                        if (activity.chatter) {
                            activity.chatter.refresh();
                        }
                    },
                },
            });
        }

        /**
         * @param {mail.activity} activity
         */
        async send(activity) {
            await this.async(() => this.env.services.rpc({
                model: activity.res_model,
                method: 'activity_send_mail',
                args: [[activity.res_id], this.id],
            }));
            if (activity.chatter) {
                activity.chatter.refresh();
            }
        }

    }

    MailTemplate.fields = {
        activities: many2many('mail.activity', {
            inverse: 'mailTemplates',
        }),
        id: attr(),
        name: attr(),
    };

    MailTemplate.modelName = 'mail.mail_template';

    return MailTemplate;
}

registerNewModel('mail.mail_template', factory);

});
