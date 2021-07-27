/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useStore } from '@mail/component_hooks/use_store/use_store';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model/use_update_to_model';
import { ThreadIcon } from '@mail/components/thread_icon/thread_icon';

const { Component } = owl;

const components = { ThreadIcon };

export class ThreadViewTopbar extends Component {

    /**
     * @override
     */
    setup() {
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const threadViewTopBar = this.env.models['mail.thread_view_topbar'].get(props.localId);
            const thread = threadViewTopBar && threadViewTopBar.thread;
            const threadView = threadViewTopBar && threadViewTopBar.threadView;
            return {
                inbox: this.env.messaging.inbox,
                starred: this.env.messaging.starred,
                thread,
                threadChannelType: thread && thread.channel_type,
                threadDescription: thread && thread.description,
                threadDisplayName: thread && thread.displayName,
                threadModel: thread && thread.model,
                threadViewMessagesLength: threadView && threadView.messages.length,
                threadViewTopBar,
                threadViewTopBarIsEditingThreadName: threadViewTopBar && threadViewTopBar.isEditingThreadName,
                threadViewTopBarIsMouseOverThreadName: threadViewTopBar && threadViewTopBar.isMouseOverThreadName,
                threadViewTopBarPendingThreadName: threadViewTopBar && threadViewTopBar.pendingThreadName,
            };
        });
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
