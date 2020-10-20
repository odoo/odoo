/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { useAutofocus, useService } from "@web/core/utils/hooks";

const { Component, useState } = owl;
const { useRef } = owl.hooks;

class ThreadSearchBox extends Component {

    setup() {
        this.state = useState({ searchText: this.thread.searchedText });
        useAutofocus();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread|undefined}
     */
    get thread() {
        return this.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }

    /**
     * Saves the text input state in store
     */
    saveStateInStore() {
        this.thread.update({ searchedText: this.state.searchText });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onFocusout() {
        this.saveStateInStore();
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        if (ev.key === 'Enter') {
            this.saveStateInStore();
        }
    }

}

Object.assign(ThreadSearchBox, {
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadSearchBox',
});

registerMessagingComponent(ThreadSearchBox);
