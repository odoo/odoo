import publicWidget from '@web/legacy/js/public/public_widget';
import { addLoadingEffect } from '@web/core/utils/ui';

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
        if (!ev.defaultPrevented) {
            const btnEl = ev.currentTarget.querySelector('button[type="submit"]');
            const removeLoadingEffect = addLoadingEffect(btnEl);
            const oldPreventDefault = ev.preventDefault.bind(ev);
            ev.preventDefault = () => {
                removeLoadingEffect();
                oldPreventDefault();
            };
        }
    },
});
