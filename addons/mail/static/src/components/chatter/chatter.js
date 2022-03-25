/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from '@web/legacy/legacy_component';

export class Chatter extends LegacyComponent {

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
