odoo.define('web/static/src/js/services/keyboard_navigation_service.js', function (require) {
    "use strict";

    const AbstractService = require('web.AbstractService');
    const core = require('web.core');

    let id = 0;

    const KeyboardNavigationService = AbstractService.extend({
        BUFFER_DELAY: 1000,
        init() {
            this._super(...arguments);
            this._listeners = {};
            this._activeCallbacks = null;
            this._lastKeyTime = Date.now();
            this._keyDownHandler = this._onKeyDown.bind(this);
        },
        /**
         * Registers a callback to execute on keydown events.
         * @param {function} callback
         * @returns {integer} the token to use to unregister the callback
         */
        register(callback) {
            if (Object.keys(this._listeners).length === 0) {
                this._startListening();
            }
            let token = id++;
            this._listeners[token] = callback;
            return token;
        },
        /**
         * Unregisters a callback.
         * @param {integer} token the token returned when the callback has been
         *   registered
         */
        unregister(token) {
            delete this._listeners[token];
            if (Object.keys(this._listeners).length === 0) {
                this._stopListening();
            }
        },

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _startListening() {
            document.addEventListener('keydown', this._keyDownHandler);
        },
        /**
         * @private
         */
        _stopListening() {
            document.removeEventListener('keydown', this._keyDownHandler);
        },

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * Reacts to keydown events: clears the buffers if necessary, processes
         * the current event, and notifies all listeners.
         * @private
         * @param {KeyboardEvent} ev
         */
        _onKeyDown(ev) {
            // TODO: detect modifiers keydown (e.g. shift)
            // TODO: keep control keys as is ('Escape' instead of 'escape')
            // TODO: handle numbers (code = DIGITX)
            console.log(`key ${ev.key}, code ${ev.code}, location ${ev.location}`);
            if (ev.key !== 'Escape' && !ev.altKey && ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) { // FIXME
                return;
            }
            // clear active callbacks after a delay
            const now = Date.now();
            if (now - this._lastKeyTime > this.BUFFER_DELAY) {
                this._activeCallbacks = null;
            }
            this._lastKeyTime = now;

            // execute listener (i.e. all) or active callbacks if we are in the
            // second level accesskey mode
            const keystroke = {
                key: ev.key.toUpperCase(),
                altKey: ev.altKey,
                ctrlKey: ev.ctrlKey,
                shiftKey: ev.shiftKey,
                _originalEvent: ev,
            };
            const callbacks = this._activeCallbacks || Object.values(this._listeners);
            const secondLvl = !!this._activeCallbacks;
            const activeCallbacks = [];
            callbacks.forEach(callback => {
                const enterSecondLvl = callback(keystroke, secondLvl);
                if (enterSecondLvl) {
                    activeCallbacks.push(callback);
                }
            });
            this._activeCallbacks = activeCallbacks.length ? activeCallbacks : null;
        },
    });

    core.serviceRegistry.add('keyboard_navigation', KeyboardNavigationService);

    return KeyboardNavigationService;
});
