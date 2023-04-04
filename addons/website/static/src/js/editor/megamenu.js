/** @odoo-module **/

import core from 'web.core';
import publicWidget from 'web.public.widget';

publicWidget.registry.hoverableDropdown.include({
    /**
     * @override
     */
    start() {
        if (this.editableMode) {
            this._onPageClick = this._onPageClick.bind(this);
            this.el.closest('#wrapwrap').addEventListener('click', this._onPageClick);
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy() {
        if (this.editableMode) {
            this.el.closest('#wrapwrap').removeEventListener('click', this._onPageClick);
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Hides all opened menues.
     *
     * @private
     */
    _hideMenues() {
        core.bus.trigger('deactivate_snippet_if_any', {data: {
            targetCondition: el => {
                const headerEl = el.closest('header');
                const shownMenuEl = headerEl.querySelector('.nav-item.dropdown.show');
                return shownMenuEl && headerEl === this.el;
            },
        }});
        for (const el of this.el.querySelectorAll('.nav-item.dropdown.show')) {
            el.classList.remove('show');
            for (const toggleEl of el.querySelectorAll('.dropdown-toggle')) {
                toggleEl.setAttribute('aria-expanded', 'false');
            }
            for (const menuEl of el.querySelectorAll('.dropdown-menu')) {
                menuEl.classList.remove('show');
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the page is clicked anywhere.
     * Closes the shown menu if the click is outside of it.
     *
     * @private
     * @param {Event} ev
     */
    _onPageClick(ev) {
        if (ev.target.closest('.dropdown.show')) {
            return;
        }
        this._hideMenues();
    },
    /**
     * @override
     */
    _onMouseEnter(ev) {
        if (this.editableMode && ev.target.classList.contains('o_mega_menu_toggle')) {
            // Hide any other sub-menu.
            this._hideMenues();
        }
        this._super(...arguments);
    },
    /**
     * @override
     */
    _onMouseLeave(ev) {
        if (this.editableMode) {
            // Cancel handling from view mode.
            return;
        }
        this._super(...arguments);
    },
});
