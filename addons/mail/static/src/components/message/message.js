/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, useRef } = owl;

export class Message extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'contentRef', refName: 'content' });
        useRefToModel({ fieldName: 'notificationIconRef', refName: 'notificationIcon' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
        /**
         * Reference to element containing the prettyBody. Useful to be able to
         * replace prettyBody with new value in JS (which is faster than t-raw).
         */
        this._prettyBodyRef = useRef('prettyBody');
    }

    /**
     * @returns {MessageView}
     */
    get messageView() {
        return this.props.record;
    }

    /**
     * @private
     */
    _update() {
            this._prettyBodyRef.el.innerHTML = this.messageView.message.prettyBody;
    }

}

Object.assign(Message, {
    props: { record: Object },
    template: 'mail.Message',
});

registerMessagingComponent(Message);
