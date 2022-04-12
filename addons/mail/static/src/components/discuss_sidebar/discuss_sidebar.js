/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussSidebar extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useUpdate({ func: () => this._update() });
        useRefToModel({ fieldName: 'quickSearchInputRef', modelName: 'DiscussView', refName: 'quickSearchInput' });
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
        if (this.discussView.quickSearchInputRef.el) {
            this.discussView.quickSearchInputRef.el.value = this.discussView.discuss.sidebarQuickSearchValue;
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
        this.discussView.discuss.onInputQuickSearch(this.discussView.quickSearchInputRef.el.value);
    }

}

Object.assign(DiscussSidebar, {
    props: { localId: String },
    template: 'mail.DiscussSidebar',
});

registerMessagingComponent(DiscussSidebar);
