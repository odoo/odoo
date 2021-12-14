/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model/use_update_to_model';

export class WelcomeView extends owl.Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'guestNameInputRef', modelName: 'WelcomeView', propNameAsRecordLocalId: 'localId', refName: 'guestNameInput' });
        useUpdateToModel({ methodName: 'onComponentUpdate', modelName: 'WelcomeView', propNameAsRecordLocalId: 'localId' });
    }

    /**
     * @returns {WelcomeView}
     */
    get welcomeView() {
        return this.messaging && this.messaging.models['WelcomeView'].get(this.props.localId);
    }

}

Object.assign(WelcomeView, {
    props: { localId: String },
    template: 'mail.WelcomeView',
});

registerMessagingComponent(WelcomeView);
