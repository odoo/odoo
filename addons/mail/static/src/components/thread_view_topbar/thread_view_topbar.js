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
        useRefToModel({ fieldName: 'guestNameInputRef', refName: 'guestNameInput' });
        useRefToModel({ fieldName: 'inviteButtonRef', refName: 'inviteButton' });
        useRefToModel({ fieldName: 'threadNameInputRef', refName: 'threadNameInput' });
        useRefToModel({ fieldName: 'threadDescriptionInputRef', refName: 'threadDescriptionInput' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ThreadViewTopbar}
     */
    get threadViewTopbar() {
        return this.props.record;
    }

}

Object.assign(ThreadViewTopbar, {
    props: { record: Object },
    template: 'mail.ThreadViewTopbar',
});

registerMessagingComponent(ThreadViewTopbar);
