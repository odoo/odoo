/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from '@web/core/dialog/dialog';
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';
import { useChildRef, useService } from '@web/core/utils/hooks';
import { Component } from "@odoo/owl";

export class AddSocialStreamDialog extends Component {
    static components = { Dialog };
    static template = "social.AddSocialStreamDialog";
    static props = {
        title: String,
        socialAccounts: Array,
        isSocialManager: Boolean,
        onSaved: Function,
        close: Function,
        socialMedia: Object,
        companies: Array,
    };

    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.modalRef = useChildRef();
        this.orm = useService('orm');
    }

    _onClickSocialAccount(event) {
        const target = event.currentTarget;
        this.dialog.add(FormViewDialog, {
            title: _t('Add a Stream'),
            resModel: 'social.stream',
            context: {
                default_media_id: parseInt(target.dataset.mediaId),
                default_account_id: parseInt(target.dataset.accountId),
                form_view_ref: 'social.social_stream_view_form_wizard',
            },
            onRecordSaved: (result) => this.props.onSaved(result),
        });
        this.props.close();
    }

    _onClickSocialMedia(event) {
        const mediaId = parseInt(event.currentTarget.dataset.mediaId);
        const selectCompany = this.modalRef.el.querySelector('select[name="company_id"]');
        const companyId = selectCompany ? parseInt(selectCompany.value) || 0 : undefined;

        this.orm.call('social.media', 'action_add_account', [mediaId], {
            company_id: companyId
        }).then((action) => {
            document.location = action.url;
        });
    }

}
