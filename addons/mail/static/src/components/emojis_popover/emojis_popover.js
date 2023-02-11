/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import emojis from '@mail/js/emojis';

const { Component } = owl;

export class EmojisPopover extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.emojis = emojis;
        useUpdate({ func: () => this._update() });
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        this.trigger('o-popover-compute');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    close() {
        this.trigger('o-popover-close');
    }

    /**
     * Returns whether the given node is self or a children of self.
     *
     * @param {Node} node
     * @returns {boolean}
     */
    contains(node) {
        return Boolean(this.el && this.el.contains(node));
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickEmoji(ev) {
        this.close();
        this.trigger('o-emoji-selection', {
            unicode: ev.currentTarget.dataset.unicode,
        });
    }

}

Object.assign(EmojisPopover, {
    props: {},
    template: 'mail.EmojisPopover',
});

registerMessagingComponent(EmojisPopover);
