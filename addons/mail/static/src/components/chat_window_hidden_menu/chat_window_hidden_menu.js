/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted, onPatched, useRef } = owl;

export class ChatWindowHiddenMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        /**
         * Reference of the dropup list. Useful to auto-set max height based on
         * browser screen height.
         */
        this._listRef = useRef('list');
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
        this._applyListHeight();
        this._applyOffset();
    }

    /**
     * @private
     */
    _applyListHeight() {
        const device = this.messaging.device;
        const height = device.globalWindowInnerHeight / 2;
        this._listRef.el.style['max-height'] = `${height}px`;
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
