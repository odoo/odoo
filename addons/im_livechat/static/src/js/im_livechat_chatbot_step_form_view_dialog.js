/** @odoo-module alias=im_livechat.ChatbotStepFormViewDialog **/

import { _t } from 'web.core';
import FormViewDialog from 'web.view_dialogs';

/**
 * Override of the FormViewDialog.
 * We essentially ensure to trigger a form save every time a step is added.
 */
const ChatbotStepFormViewDialog = FormViewDialog.FormViewDialog.extend({
    /**
     * Overload the default buttons to add our custom ones.
     * The main goal is to trigger a full chatbot.script form save every time a step is added.
     * See ChatbotFormController#_saveFormBeforeNewStep()
     */
    init: function (parent, options) {
        this._super(...arguments);

        const readonly = _.isNumber(this.res_id) && this.readonly;
        this.buttons = [{
            text: _t("Save & Close"),
            classes: "btn-primary",
            click: () => {
                this._save().then(() => {
                    parent.trigger_up('chatbot_save_form', {
                        callback: () => {
                            this.close();
                        }
                    });
                });
            },
        }, {
            text: _t("Save & New"),
            classes: "btn-primary",
            click: () => {
                this._save().then(() => {
                    parent.trigger_up('chatbot_save_form', {
                        callback: () => {
                            parent.trigger_up('chatbot_add_step', {
                                callback: () => {this.close();}
                            });
                        }
                    });
                });
            },
        }, {
            text: options.close_text || (readonly ? _t("Close") : _t("Discard")),
            classes: "btn-secondary o_form_button_cancel",
            close: true,
            hotkey: 'j',
            click: () => {
                if (!readonly) {
                    this.form_view.model.discardChanges(this.form_view.handle, {
                        // no need to rollback locally as we save the steps in-between each creation
                        rollback: false,
                    });
                }
            },
        }];
    }
});

export default ChatbotStepFormViewDialog;
