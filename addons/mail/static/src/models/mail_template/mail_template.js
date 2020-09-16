odoo.define('mail/static/src/models/mail_template/mail_template.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many } = require('mail/static/src/model/model_field_utils.js');

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
                    default_res_id: activity.__mfield_res_id(this),
                    default_model: activity.__mfield_res_model(this),
                    default_use_template: true,
                    default_template_id: this.__mfield_id(this),
                    force_email: true,
                },
            };
            this.env.bus.trigger('do-action', {
                action,
                options: {
                    on_close: () => {
                        if (activity.__mfield_chatter(this)) {
                            activity.__mfield_chatter(this).refresh();
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
                model: activity.__mfield_res_model(this),
                method: 'activity_send_mail',
                args: [[activity.__mfield_res_id(this)], this.__mfield_id(this)],
            }));
            if (activity.__mfield_chatter(this)) {
                activity.__mfield_chatter(this).refresh();
            }
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

    }

    MailTemplate.fields = {
        __mfield_activities: many2many('mail.activity', {
            inverse: '__mfield_mailTemplates',
        }),
        __mfield_id: attr(),
        __mfield_name: attr(),
    };

    MailTemplate.modelName = 'mail.mail_template';

    return MailTemplate;
}

registerNewModel('mail.mail_template', factory);

});
