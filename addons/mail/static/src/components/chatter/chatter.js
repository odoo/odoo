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
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'scrollPanelRef', refName: 'scrollPanel' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Chatter}
     */
    get chatter() {
        return this.props.record;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _notifyRendered() {
        this.trigger('o-chatter-rendered', {
            thread: this.chatter.thread,
        });
    }

    /**
     * @private
     */
    _update() {
        if (this.chatter.thread) {
            this._notifyRendered();
        }
    }

}

Object.assign(Chatter, {
    props: { record: Object },
    template: 'mail.Chatter',
});

registerMessagingComponent(Chatter);
