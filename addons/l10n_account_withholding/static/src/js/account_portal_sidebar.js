/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { escape } from "@web/core/utils/strings";
import publicWidget from "@web/legacy/js/public/public_widget";
import { post } from "@web/core/network/http_service";
import AccountPortalSidebar from "@account/js/account_portal_sidebar";
import {Component} from "@odoo/owl";

publicWidget.registry.AccountPortalSidebarWithholding = AccountPortalSidebar.extend({
    events: {
        'click .o_upload_withh_cert_btn': '_onUploadButtonClick',
        'change .o_upload_withholding_tax_cert_file_input': '_onFileInputChange',
    },

    init() {
        this._super(...arguments);
        this.notification = this.bindService("notification");
    },

    /**
     * @override
     */
    start: function () {
        let def = this._super.apply(this, arguments);

        this.$withholdingFileInput = this.$('.o_upload_withholding_tax_cert_file_input');
        this.$withholdingFileButton = this.$('.o_upload_withh_cert_btn');

        return def;
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onUploadButtonClick: function () {
        this.$withholdingFileInput.click();
    },
    /**
     * @private
     * @returns {Promise}
     */
    async _onFileInputChange(ev) {
        // Just skip if there is no file in the input.
        if (!ev.target.files.length) {
            return;
        }

        this.$withholdingFileButton.prop('disabled', true);
        const file = ev.target.files[0];

        // Prepare and send the file to the controller.
        let data = {
            'name': file.name,
            'file': file,
            'thread_id': this.$withholdingFileButton[0].dataset.id,
            'thread_model': this.$withholdingFileButton[0].dataset.model,
            'access_token': this.$withholdingFileButton[0].dataset.token,
        };
        if (odoo.csrf_token) {
            data.csrf_token = odoo.csrf_token;
        }

        let self = this;

        // We never expect errors here.
        // If a traceback happens in the backend, we will simply raise a warning toast notification.
        return post('/my/invoices/upload_withholding_certificate', data, 'text')
            .then((response) => {
                if (response === "ok") {
                    // Ensure that the chatter displays the user message.
                    Component.env.bus.trigger('reload_chatter_content', {});
                    // Trigger a notification.
                    self.notification.add(_t('The certificate has been uploaded'), {
                        type: 'success',
                    });
                } else {
                    // In case of error, we simply notify of the issue and move on
                    self.notification.add(
                        _t("Could not save the file '%s'", escape(file.name)),
                        {type: 'warning', sticky: true}
                    );
                }
                // reset the input so that re-uploading works as well if needed, without refreshing.
                self.$withholdingFileInput[0].value = null;
                self.$withholdingFileButton.prop('disabled', false);
            });
    },
});
