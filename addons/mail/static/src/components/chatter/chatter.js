/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { LegacyComponent } from '@web/legacy/legacy_component';

const { useRef } = owl;

export class Chatter extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();
        useUpdate({ func: () => this._update() });
        useComponentToModel({ fieldName: 'component', modelName: 'Chatter' });
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
     * @returns {Chatter}
     */
    get chatter() {
        return this.messaging && this.messaging.models['Chatter'].get(this.props.localId);
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
    props: { localId: String },
    template: 'mail.Chatter',
});

registerMessagingComponent(Chatter);
