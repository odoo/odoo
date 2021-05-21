/** @odoo-module **/

export const instancePatchMessage = {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    openResendAction() {
        if (this.message_type === 'sms') {
            this.env.bus.trigger('do-action', {
                action: 'sms.sms_resend_action',
                options: {
                    additional_context: {
                        default_mail_message_id: this.id,
                    },
                },
            });
        } else {
            this._super(...arguments);
        }
    },
};
