/** @odoo-module **/

import Dialog from 'web.Dialog';

Dialog.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _isBlocking(index, el) {
        if (el.parentElement && el.parentElement.id === 'website_cookies_bar'
                && !el.classList.contains('o_cookies_popup')) {
            return false;
        }
        return this._super(...arguments);
    },
});
