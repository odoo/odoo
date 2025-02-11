/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteSaleOffcanvas = publicWidget.Widget.extend({
    selector: '#o_wsale_offcanvas',
    events: {
        'show.bs.offcanvas': '_toggleFilters',
        'hidden.bs.offcanvas': '_toggleFilters',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Unfold active filters, fold inactive ones
     *
     * @private
     * @param {Event} ev
     */
    _toggleFilters: function (ev) {
        for (const btn of this.el.querySelectorAll('button[data-status]')) {
            if(btn.classList.contains('collapsed') && btn.dataset.status == "active" || ! btn.classList.contains('collapsed') && btn.dataset.status == "inactive" ) {
                btn.click();
            }
        }
    },
});
