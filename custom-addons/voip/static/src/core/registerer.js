/* @odoo-module */
/* global SIP */

import { _t } from "@web/core/l10n/translation";

export class Registerer {
    /**
     * When sending a REGISTER request, an “expires” parameter with the value of
     * this field is added to the Contact header. It is used to indicate how
     * long we would like the registration to remain valid.
     * Note however that the definitive value is decided by the server based on
     * its own policy and may therefore differ.
     *
     * The library automatically renews the registration for the same duration
     * shortly before it expires.
     *
     * The value is expressed in seconds.
     */
    static EXPIRATION_INTERVAL = 3600;
    /**
     * Possible values:
     * - SIP.RegistererState.Initial
     * - SIP.RegistererState.Registered
     * - SIP.RegistererState.Unregistered
     * - SIP.RegistererState.Terminated
     */
    state;
    /**
     * An instance of the Registerer class from the SIP.js library. It shouldn't
     * be used outside of this class; only this class is responsible for
     * interfacing with this object.
     */
    __sipJsRegisterer;

    constructor(voip, sipJsUserAgent) {
        this.voip = voip;
        this.__sipJsRegisterer = new SIP.Registerer(sipJsUserAgent, {
            expires: Registerer.EXPIRATION_INTERVAL,
        });
        this.__sipJsRegisterer.stateChange.addListener((state) => this._onStateChanged(state));
    }

    /**
     * Sends the REGISTER request to the Registrar.
     */
    register() {
        this.__sipJsRegisterer.register({
            requestDelegate: {
                onReject: (response) => this._onRegistrationRejected(response),
            },
        });
    }

    /**
     * Triggered when receiving a response with status code 4xx, 5xx, or 6xx to
     * the REGISTER request.
     *
     * @param {SIP.IncomingResponse} response The server final response to the
     * REGISTER request.
     */
    _onRegistrationRejected(response) {
        const errorMessage = _t("Registration rejected: %(statusCode)s %(reasonPhrase)s.", {
            statusCode: response.message.statusCode,
            reasonPhrase: response.message.reasonPhrase,
        });
        const help = (() => {
            switch (response.message.statusCode) {
                case 401: // Unauthorized
                    return _t(
                        "The server failed to authenticate you. Please have an administrator verify that you are reaching the right server (PBX server IP in the General Settings) and that the credentials in your user preferences are correct."
                    );
                case 503: // Service Unavailable
                    return _t(
                        "The error may come from the transport layer. Please have an administrator verify the websocket server URL in the General Settings. If the problem persists, this is probably an issue with the server."
                    );
                default:
                    return _t(
                        "Please try again later. If the problem persists, you may want to ask an administrator to check the configuration."
                    );
            }
        })();
        this.voip.triggerError(`${errorMessage}\n\n${help}`);
    }

    _onStateChanged(newState) {
        this.state = newState;
        if (newState === SIP.RegistererState.Registered) {
            this.voip.resolveError();
        }
    }
}
