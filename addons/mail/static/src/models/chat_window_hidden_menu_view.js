/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ChatWindowHiddenMenuView',
    lifecycleHooks: {
        _created() {
            document.addEventListener('click', this._onClickCaptureGlobal, true);
        },
        _willDelete() {
            document.removeEventListener('click', this._onClickCaptureGlobal, true);
        },
    },
    recordMethods: {
        applyListHeight() {
            const device = this.messaging.device;
            const height = device.globalWindowInnerHeight / 2;
            this.listRef.el.style['max-height'] = `${height}px`;
        },
        applyOffset() {
            const textDirection = this.messaging.locale.textDirection;
            const offsetFrom = textDirection === 'rtl' ? 'left' : 'right';
            const oppositeFrom = offsetFrom === 'right' ? 'left' : 'right';
            const offset = this.owner.visual.hiddenMenuOffset;
            this.component.root.el.style[offsetFrom] = `${offset}px`;
            this.component.root.el.style[oppositeFrom] = 'auto';
        },
        onComponentUpdate() {
            this.applyListHeight();
            this.applyOffset();
        },
        /**
         * Closes the menu when clicking outside.
         * Must be done as capture to avoid stop propagation.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClickCaptureGlobal(ev) {
            if (!this.component || !this.component.root.el || this.component.root.el.contains(ev.target)) {
                return;
            }
            this.owner.closeHiddenMenu();
        }
    },
    fields: {
        component: attr(),
        isOpen: attr({
            default: false,
        }),
        items: many('ChatWindowHiddenMenuItemView', {
            compute() {
                return this.owner.hiddenChatWindowHeaderViews.map(chatWindowHeaderView => ({ chatWindowHeaderView }));
            },
            inverse: 'owner',
        }),
        lastItem: one('ChatWindowHiddenMenuItemView', {
            compute() {
                if (this.items.length === 0) {
                    return clear();
                }
                return this.items[this.items.length - 1];
            },
        }),
        /**
         * Reference of the dropup list. Useful to auto-set max height based on
         * browser screen height.
         */
        listRef: attr(),
        owner: one('ChatWindowManager', {
            identifying: true,
            inverse: 'hiddenMenuView',
        }),
    },
});
