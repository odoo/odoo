/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ComposerTextInputView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'mirroredTextareaRef', refName: 'mirroredTextarea' });
        useRefToModel({ fieldName: 'textareaRef', refName: 'textarea' });
        /**
         * Updates the composer text input content when composer is mounted
         * as textarea content can't be changed from the DOM.
         */
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    /**
     * @returns {ComposerTextInputView}
     */
    get composerTextInputView() {
        return this.props.record;
    }

}

Object.assign(ComposerTextInputView, {
    props: { record: Object },
    template: 'mail.ComposerTextInputView',
});

registerMessagingComponent(ComposerTextInputView);
