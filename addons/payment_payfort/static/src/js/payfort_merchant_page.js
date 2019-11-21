odoo.define('payment_payfort.merchant_page_return', function(require) {
'use strict';

/**
 * Merchant page return; this widget will run both when the customer returns from
 * the tokenization process *and* from the 3D-Secure authetntication of such a tokenization
 * (if needed). The widget will first be opened in an iframe, when the customer returns from
 * the tokenization form of Payfort. This tokenization is immediately followed by a validation
 * transaction done in the controller.
 *
 * If that tx triggered a 3D-S flow, this widget will open the authentication window of that tx
 * in a popup. This popup will redirect to the same route and the controller will process the result.
 * If the 3DS authentication was successful (and the token is thus active), the popup window will
 * dispatch a custom event to its parent (the iframe), which will itself dispatch an event to its
 * parent frameElement (the payment form).
 *
 * If no authentication is required, the iframe will send its token information to its parent
 * frameElement (the payment form).
 */

var publicWidget = require('web.public.widget');

publicWidget.registry.portalDetails = publicWidget.Widget.extend({
    selector: '#oe_payfort_merchant_page_return',
    events: {
        'click .oe_payfort_open_3ds': '_authRedirect',
        'click .oe_payfort_close_modal': 'closeModal',
    },
    /**
     * Parse the DOM element data attributes to finish initialization of the widget.
     * @override
     */
    start: async function() {
        const result = await this._super.apply(this, arguments);
        this.authUrl = this.el.dataset.authUrl;
        this.tokenId = this.el.dataset.tokenId;

        // check if we need to open an iframe or not
        if (this.authUrl) {
            /* we are in a tokenization return iframe hosted on the odoo payment page
                * that is about to open a popup window for 3DS authentication
                * listen for events from that 3DS popup and forward to the frame parent
                */
            this.el.addEventListener('odoo.payfort.auth.return', (ev) => {
                ev.stopPropagation();
                const { success, tokenId } = ev.detail;
                this.notifyParent(success, tokenId);
            });
            this._authRedirect();
        } else {
            // no 3DS needed, we can notify the payment page that the token is ready
            this.notifyParent(true, this.tokenId);
        }
        return result;
    },

    /**
     * Notify the calling window (either the payment form or another instance of this
     * widget) of the tokenization process result.
     * @param {Boolean} success - whether the tokenization was successful or not
     * @param {Integer} tokenId - the db id of the token that was created
     */
    notifyParent: function(success, tokenId) {
        const data = {
            success,
            tokenId,
        };
        if (window.frameElement) {
            /*
                * we are in an iframe, meaning that there was no 3D-Secure validation
                * the token is valid, the validation tx was refunded: we can proceed with
                * the payment using this token
                */
            const tokenEvent = new CustomEvent(
                'odoo.payfort.token.return',
                {
                    bubbles: true,
                    detail: data,
                }
            );
            window.frameElement.dispatchEvent(tokenEvent);
        } else {
            /*
                *  we are in a 3D-secure popup, the parent of this popup is the iframe from the
                *  tokenization process (which runs the same code as this window). Notify it that
                * the 3DS validation is done and successful, so that it may notify its own parent
                * that the payment token is ready to be used.
                */
            const authEvent = new CustomEvent('odoo.payfort.auth.return', {
                bubbles: true,
                detail: data,
            });
            // check that the parent is the same origin
            if (!this._isParentSameOrigin()) {
                return;
            }
            const eventTarget = window.opener.document.getElementById(
                'oe_payfort_merchant_page_return'
            );
            eventTarget.dispatchEvent(authEvent);
            // display confirmation for 1.5 sec before closing the window
            // the event has already been dispatch, so it does not matter if the
            // customer closes the window before that
            setTimeout(() => {
                window.close();
            }, 1500);
        }
    },

    /**
     * Open a popup window for a 3DS authentication flow.
     */
    _authRedirect: function() {
        return window.open(
            this.authUrl,
            'payfortAuthWindow',
            'height=550,width=550,top=100,left=100'
        );
    },

    /**
     * Close the window/popup after a failed tokenization by sending a failure event,
     * the window will be automatically closed after the event is dispatched.
     */
    closeModal: function() {
        this.notifyParent(false, null);
    },

    /**
     * Check if the parent window is from the same origin as this one to avoid sending
     * data to any other website.
     */
    _isParentSameOrigin() {
        if (!window.opener) {
            return false;
        }
        return window.opener.location.origin === window.location.origin;
    },
});
});
