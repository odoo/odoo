/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadViewTopbar extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'guestNameInputRef', modelName: 'ThreadViewTopbar', refName: 'guestNameInput' });
        useRefToModel({ fieldName: 'inviteButtonRef', modelName: 'ThreadViewTopbar', refName: 'inviteButton' });
        useRefToModel({ fieldName: 'threadNameInputRef', modelName: 'ThreadViewTopbar', refName: 'threadNameInput' });
        useRefToModel({ fieldName: 'threadDescriptionInputRef', modelName: 'ThreadViewTopbar', refName: 'threadDescriptionInput' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'ThreadViewTopbar' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ThreadViewTopbar}
     */
    get threadViewTopbar() {
        return this.messaging && this.messaging.models['ThreadViewTopbar'].get(this.props.localId);
    }

}

Object.assign(ThreadViewTopbar, {
    props: { localId: String },
    template: 'mail.ThreadViewTopbar',
});

registerMessagingComponent(ThreadViewTopbar);
