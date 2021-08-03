/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model/use_update_to_model';
import { ChannelInvitationForm } from '@mail/components/channel_invitation_form/channel_invitation_form';
import { ThreadIcon } from '@mail/components/thread_icon/thread_icon';

const { Component } = owl;

const components = { ChannelInvitationForm, ThreadIcon };

export class ThreadViewTopbar extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useShouldUpdateBasedOnProps();
        useModels();
        useRefToModel({ fieldName: 'threadNameInputRef', modelName: 'mail.thread_view_topbar', propNameAsRecordLocalId: 'localId', refName: 'threadNameInput' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'mail.thread_view_topbar', propNameAsRecordLocalId: 'localId' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread_view_topbar}
     */
    get threadViewTopBar() {
        return this.env.models['mail.thread_view_topbar'].get(this.props.localId);
    }

}

Object.assign(ThreadViewTopbar, {
    components,
    props: {
        localId: String,
    },
    template: 'mail.ThreadViewTopbar',
});
