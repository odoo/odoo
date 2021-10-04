/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

const { Component } = owl;
const { useRef } = owl.hooks;

export class Chatter extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useUpdate({ func: () => this._update() });
        useRefToModel({ fieldName: 'threadRef', modelName: 'mail.chatter', propNameAsRecordLocalId: 'chatterLocalId', refName: 'thread' });
        /**
         * Reference of the scroll Panel (Real scroll element). Useful to pass the Scroll element to
         * child component to handle proper scrollable element.
         */
        this._scrollPanelRef = useRef('scrollPanel');
        this.getScrollableElement = this.getScrollableElement.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.chatter}
     */
    get chatter() {
        return this.messaging && this.messaging.models['mail.chatter'].get(this.props.chatterLocalId);
    }

    /**
     * @returns {Element|undefined} Scrollable Element
     */
    getScrollableElement() {
        if (!this._scrollPanelRef.el) {
            return;
        }
        return this._scrollPanelRef.el;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _notifyRendered() {
        this.trigger('o-chatter-rendered', {
            attachments: this.chatter.thread.allAttachments,
            thread: this.chatter.thread.localId,
        });
    }

    /**
     * @private
     */
    _update() {
        if (!this.chatter) {
            return;
        }
        if (this.chatter.thread) {
            this._notifyRendered();
        }
    }

}

Object.assign(Chatter, {
    props: {
        chatterLocalId: String,
    },
    template: 'mail.Chatter',
});

registerMessagingComponent(Chatter);
