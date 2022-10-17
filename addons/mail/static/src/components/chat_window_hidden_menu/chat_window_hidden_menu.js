/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onPatched } = owl;

export class ChatWindowHiddenMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'listRef', refName: 'list' });
        onMounted(() => this._mounted());
        onPatched(() => this._patched());
    }

    _mounted() {
        if (!this.root.el) {
            return;
        }
        this._apply();
    }

    _patched() {
        if (!this.root.el) {
            return;
        }
        this._apply();
    }

    /**
     * @returns {ChatWindowHiddenMenuView}
     */
    get chatWindowHiddenMenuView() {
        return this.props.record;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _apply() {
        if (!this.messaging) {
            return;
        }
        this.chatWindowHiddenMenuView.applyListHeight();
        this.chatWindowHiddenMenuView.applyOffset();
    }

}

Object.assign(ChatWindowHiddenMenu, {
    props: { record: Object },
    template: 'mail.ChatWindowHiddenMenu',
});

registerMessagingComponent(ChatWindowHiddenMenu);
