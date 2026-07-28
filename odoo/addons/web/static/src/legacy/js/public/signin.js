/** @odoo-module */

import dom from '@web/legacy/js/core/dom';
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.login = publicWidget.Widget.extend({
    selector: '.oe_login_form',
    events: {
        'submit': '_onSubmit',
    },

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * Prevents the user from crazy clicking:
     * Gives the button a loading effect if preventDefault was not already
     * called and modifies the preventDefault function of the event so that the
     * loading effect is removed if preventDefault() is called in a following
     * customization.
     *
     * @private
     * @param {Event} ev
     */
    _onSubmit(ev) {
        if (!ev.isDefaultPrevented()) {
            const btnEl = ev.currentTarget.querySelector('button[type="submit"]');
            const removeLoadingEffect = dom.addButtonLoadingEffect(btnEl);
            const oldPreventDefault = ev.preventDefault.bind(ev);
            ev.preventDefault = () => {
                removeLoadingEffect();
                oldPreventDefault();
            };
        }
    },
});
