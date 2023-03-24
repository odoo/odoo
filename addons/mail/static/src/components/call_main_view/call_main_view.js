/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onWillUnmount } = owl;

export class CallMainView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'tileContainerRef', refName: 'tileContainer', });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
        onMounted(() => {
            this.resizeObserver = new ResizeObserver(() => this.callMainView.onResize());
            this.resizeObserver.observe(this.root.el);
        });
        onWillUnmount(() => this.resizeObserver.disconnect());
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {CallMainView}
     */
    get callMainView() {
        return this.props.record;
    }
}

Object.assign(CallMainView, {
    props: { record: Object },
    template: 'mail.CallMainView',
});

registerMessagingComponent(CallMainView);
