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
        useRefToModel({ fieldName: 'quickSearchInputRef', refName: 'quickSearchInput' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DiscussView}
     */
    get discussView() {
        return this.props.record;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        if (this.discussView.quickSearchInputRef.el) {
            this.discussView.quickSearchInputRef.el.value = this.discussView.discuss.sidebarQuickSearchValue;
        }
    }

}

Object.assign(DiscussSidebar, {
    props: { record: Object },
    template: 'mail.DiscussSidebar',
});

registerMessagingComponent(DiscussSidebar);
