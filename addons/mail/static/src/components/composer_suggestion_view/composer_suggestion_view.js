/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ComposerSuggestionView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ComposerSuggestionView}
     */
    get composerSuggestionView() {
        return this.props.record;
    }

}

Object.assign(ComposerSuggestionView, {
    props: { record: Object },
    template: 'mail.ComposerSuggestionView',
});

registerMessagingComponent(ComposerSuggestionView);
