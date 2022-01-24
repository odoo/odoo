/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';

const { Component, useRef } = owl;

export class DiscussSidebar extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useUpdate({ func: () => this._update() });
        /**
         * Reference of the quick search input. Useful to filter channels and
         * chats based on this input content.
         */
        this._quickSearchInputRef = useRef('quickSearchInput');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DiscussView}
     */
    get discussView() {
        return this.messaging && this.messaging.models['DiscussView'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        if (!this.discussView) {
            return;
        }
        if (this._quickSearchInputRef.el) {
            this._quickSearchInputRef.el.value = this.discussView.discuss.sidebarQuickSearchValue;
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onInputQuickSearch(ev) {
        ev.stopPropagation();
        this.discussView.discuss.onInputQuickSearch(this._quickSearchInputRef.el.value);
    }

}

Object.assign(DiscussSidebar, {
    props: { localId: String },
    template: 'mail.DiscussSidebar',
});

registerMessagingComponent(DiscussSidebar);
