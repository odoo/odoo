odoo.define('website.ripple_effect', function (require) {
'use strict';

const publicWidget = require('web.public.widget');

publicWidget.registry.RippleEffect = publicWidget.Widget.extend({
    selector: '.btn, .dropdown-toggle, .dropdown-item',
    events: {
        'click': '_onClick',
    },
    duration: 350,

    /**
     * @override
     */
    start: async function () {
        this.diameter = Math.max(this.$el.outerWidth(), this.$el.outerHeight());
        this.offsetX = this.$el.offset().left;
        this.offsetY = this.$el.offset().top;
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super(...arguments);
        if (this.rippleEl) {
            this.rippleEl.remove();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {boolean} [toggle]
     */
    _toggleRippleEffect: function (toggle) {
        this.el.classList.toggle('o_js_ripple_effect', toggle);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClick: function (ev) {
        if (!this.rippleEl) {
            this.rippleEl = document.createElement('span');
            this.rippleEl.classList.add('o_ripple_item');
            this.rippleEl.style.animationDuration = `${this.duration}ms`;
            this.el.appendChild(this.rippleEl);
        }

        clearTimeout(this.timeoutID);
        this._toggleRippleEffect(false);

        // TO DO: In master, replace these 3 following variables by "CONST"
        // variables and remove them from the "start" where we have left them
        // only for compatibility.
        this.offsetY = this.$el.offset().top;
        this.offsetX = this.$el.offset().left;
        // The diameter need to be recomputed because a change of window width
        // can affect the size of a button (e.g. media queries).
        this.diameter = Math.max(this.$el.outerWidth(), this.$el.outerHeight());

        this.rippleEl.style.width = `${this.diameter}px`;
        this.rippleEl.style.height = `${this.diameter}px`;
        this.rippleEl.style.top = `${ev.pageY - this.offsetY - this.diameter / 2}px`;
        this.rippleEl.style.left = `${ev.pageX - this.offsetX - this.diameter / 2}px`;

        this._toggleRippleEffect(true);
        this.timeoutID = setTimeout(() => this._toggleRippleEffect(false), this.duration);
    },
});
});
