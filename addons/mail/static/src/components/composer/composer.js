/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class Composer extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'buttonEmojisRef', refName: 'buttonEmojis' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ComposerView}
     */
    get composerView() {
        return this.props.record;
    }

}

Object.assign(Composer, {
    props: { record: Object },
    template: 'mail.Composer',
});

registerMessagingComponent(Composer);
