/** @odoo-module **/

import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { useRefToModel } from "@mail/component_hooks/use_ref_to_model";
import { useUpdateToModel } from "@mail/component_hooks/use_update_to_model";
import { registerMessagingComponent } from "@mail/utils/messaging_component";

import { Transition } from "@web/core/transition";

import { Component, onWillPatch } from "@odoo/owl";

export class MessageListView extends Component {
    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: "component" });
        useRefToModel({ fieldName: "loadMoreRef", refName: "loadMore" });
        useUpdateToModel({ methodName: "onComponentUpdate" });
        /**
         * Snapshot computed during willPatch, which is used by patched.
         */
        this._willPatchSnapshot = undefined;
        onWillPatch(() => this._willPatch());
    }

    _willPatch() {
        if (!this.messageListView.exists()) {
            return;
        }
        this._willPatchSnapshot = {
            scrollHeight: this.messageListView.getScrollableElement().scrollHeight,
            scrollTop: this.messageListView.getScrollableElement().scrollTop,
        };
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {MessageListView}
     */
    get messageListView() {
        return this.props.record;
    }
}

Object.assign(MessageListView, {
    components: { Transition },
    props: { record: Object },
    template: "mail.MessageListView",
});

registerMessagingComponent(MessageListView);
