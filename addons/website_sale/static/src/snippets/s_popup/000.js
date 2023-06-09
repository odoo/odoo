/** @odoo-module **/

import PopupWidget from 'website.s_popup';

PopupWidget.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Checks if the given primary button should allow or not to close the
     * modal.
     *
     * @override
     */
    _canBtnPrimaryClosePopup(primaryBtnEl) {
        return (
            this._super(...arguments)
            && !primaryBtnEl.classList.contains("js_add_cart")
        );
    },
});

export default PopupWidget;
