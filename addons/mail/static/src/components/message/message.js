/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class Message extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'contentRef', refName: 'content' });
        useRefToModel({ fieldName: 'notificationIconRef', refName: 'notificationIcon' });
        useRefToModel({ fieldName: 'prettyBodyRef', refName: 'prettyBody' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Tell whether the message is partially visible on browser window or not.
     *
     * @returns {boolean}
     */
    isPartiallyVisible() {
        if (!this.root.el) {
            return false;
        }
        const elRect = this.root.el.getBoundingClientRect();
        if (!this.root.el.parentNode) {
            return false;
        }
        const parentRect = this.root.el.parentNode.getBoundingClientRect();
        // intersection with 5px offset
        return (
            elRect.top < parentRect.bottom + 5 &&
            parentRect.top < elRect.bottom + 5
        );
    }

    /**
     * @returns {MessageView}
     */
    get messageView() {
        return this.props.record;
    }

}

Object.assign(Message, {
    props: { record: Object },
    template: 'mail.Message',
});

registerMessagingComponent(Message);
