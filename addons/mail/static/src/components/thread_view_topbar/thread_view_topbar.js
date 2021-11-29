/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useHtmlRefToModel } from '@mail/component_hooks/use_html_ref_to_model/use_html_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model/use_update_to_model';

const { Component } = owl;

export class ThreadViewTopbar extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useHtmlRefToModel({ fieldName: 'guestNameInputRef', modelName: 'mail.thread_view_topbar', propNameAsRecordLocalId: 'localId', refName: 'guestNameInput' });
        useHtmlRefToModel({ fieldName: 'inviteButtonRef', modelName: 'mail.thread_view_topbar', propNameAsRecordLocalId: 'localId', refName: 'inviteButton' });
        useHtmlRefToModel({ fieldName: 'threadNameInputRef', modelName: 'mail.thread_view_topbar', propNameAsRecordLocalId: 'localId', refName: 'threadNameInput' });
        useHtmlRefToModel({ fieldName: 'threadDescriptionInputRef', modelName: 'mail.thread_view_topbar', propNameAsRecordLocalId: 'localId', refName: 'threadDescriptionInput' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'mail.thread_view_topbar', propNameAsRecordLocalId: 'localId' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread_view_topbar}
     */
    get threadViewTopbar() {
        return this.messaging && this.messaging.models['mail.thread_view_topbar'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickPhone(ev) {
        if (this.threadViewTopbar.thread.hasPendingRtcRequest) {
            return;
        }
        await this.threadViewTopbar.thread.toggleCall();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickCamera(ev) {
        if (this.threadViewTopbar.thread.hasPendingRtcRequest) {
            return;
        }
        await this.threadViewTopbar.thread.toggleCall({
            startWithVideo: true,
        });
    }

}

Object.assign(ThreadViewTopbar, {
    props: {
        localId: String,
    },
    template: 'mail.ThreadViewTopbar',
});

registerMessagingComponent(ThreadViewTopbar);
