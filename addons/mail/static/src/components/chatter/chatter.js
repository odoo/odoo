/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';

const { Component, useRef } = owl;

export class Chatter extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useUpdate({ func: () => this._update() });
        useComponentToModel({ fieldName: 'component', modelName: 'Chatter' });
        useRefToModel({ fieldName: 'scrollPanelRef', modelName: 'Chatter', refName: 'scrollPanel' });
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
