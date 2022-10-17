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
        this._applyOffset();
    }

    /**
     * @private
     */
    _applyOffset() {
        const textDirection = this.messaging.locale.textDirection;
        const offsetFrom = textDirection === 'rtl' ? 'left' : 'right';
        const oppositeFrom = offsetFrom === 'right' ? 'left' : 'right';
        const offset = this.messaging.chatWindowManager.visual.hiddenMenuOffset;
        this.root.el.style[offsetFrom] = `${offset}px`;
        this.root.el.style[oppositeFrom] = 'auto';
    }

}

Object.assign(ChatWindowHiddenMenu, {
    props: { record: Object },
    template: 'mail.ChatWindowHiddenMenu',
});

registerMessagingComponent(ChatWindowHiddenMenu);
