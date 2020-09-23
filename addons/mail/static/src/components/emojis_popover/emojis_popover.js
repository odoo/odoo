odoo.define('mail/static/src/components/emojis_popover/emojis_popover.js', function (require) {
'use strict';

const emojis = require('mail.emojis');

const { Component } = owl;

class EmojisPopover extends Component {

    /**
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.emojis = emojis;
    }


    mounted() {
        this._update();
    }

    patched() {
        this._update();
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
        if (!this.el) {
            return false;
        }
        return this.el.contains(node);
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

return EmojisPopover;

});
