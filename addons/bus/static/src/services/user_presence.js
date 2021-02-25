/** @odoo-module **/

/**
 * Manages the presence of the current user. Both the page visibility and the
 * laster user action are taken into account.
 */
export class UserPresence {

    constructor(env) {
        this.env = env;
        /**
         * States whether the current page is visible.
         */
        this._isCurrentPageVisible;
        /**
         * States whether any tab with Odoo is visible, including this one.
         */
         // TODO SEB update and use this value
        this._isAnyOdooTabVisible;
        /**
         * States when was the last user action in any Odoo tab. Timestamp in
         * local time and in ms.
         */
         // TODO SEB update and use this value
        this._lastActionTimestamp;
        /**
         * Set of currently registered handlers.
         */
        this._handlers = new Set();

        this._handleVisibilityChange = this._handleVisibilityChange.bind(this);
        document.addEventListener('visibilitychange', this._handleVisibilityChange);

        this._updateVisibilityState();
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @returns {boolean}
     */
    isCurrentPageVisible() {
        return this._isCurrentPageVisible;
    }

    /**
     * Registers a new handler.
     *
     * @param {function} handler will be called when a bus message is received
     *  from the server. It will be called with one param: the message that was
     *  received from the server.
     */
    registerHandler(handler) {
        this._handlers.add(handler);
    }

    /**
     * Unregisters an existing handler.
     *
     * @param {function} handler to unregister
     */
    unregisterHandler(handler) {
        this._handlers.delete(handler);
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Notifies the currently registered handlers.
     *
     * @private
     */
    _notifyHandlers() {
        for (const handler of this._handlers) {
            // Isolate each handler on its own stack to prevent any potential
            // issue in one of them to influence any other.
            setTimeout(handler);
        }
    }

    /**
     * @private
     */
    _updateVisibilityState() {
        this._isCurrentPageVisible = document.visibilityState === 'visible';
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * @private
     */
    _handleVisibilityChange() {
        this._updateVisibilityState();
        this._notifyHandlers();
    }

}

export const userPresenceService = {
    name: 'bus.user_presence',
    dependencies: ['bus.crosstab_communication'],
    deploy: env => new UserPresence(env),
};
