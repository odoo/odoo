odoo.define('point_of_sale.custom_hooks', function(require) {
    'use strict';

    const { Component, hooks } = owl;
    const { useExternalListener } = hooks;
    const { useListener } = require('web.custom_hooks');

    /**
     * Returns an object with get, set and reset methods.
     *   - get: returns the recent value of the buffer.
     *   - set(valStr): sets `valStr` as value of the buffer.
     *   - reset: set the buffer to empty string.
     *
     * When this hook is used inside a component, a keyup listener is started
     * in window. Any valid number input will be intercepted and registered to
     * the buffer inside this hook.
     *
     * When `Enter` key is pressed, the component's `triggerAtEnter` event
     * is triggerred.
     *
     * For every valid input press, the component's `triggerAtInput` event
     * is triggered.
     *
     * The buffer can also be mutated by event other than keyup and this
     * event is specified in `nonKeyboardEvent`.
     *
     * @param {Object} obj
     * @param {String} obj.decimalPoint The decimal character.
     * @param {String} obj.triggerAtEnter Event triggered when 'Enter' key is pressed.
     * @param {String} obj.triggerAtInput Event triggered for every accepted input.
     * @param {String} obj.nonKeyboardEvent Event to trigger when input from other event occurs.
     *      e.g. Clicking a numpad button can trigger an event and if it triggered
     *          `nonKeyboardEvent` then that event is intercepted here via onNonKeyboardInput.
     *          The event should carry a payload that will be checked and used as input to
     *          the buffer.
     */
    function useNumberBuffer({
        decimalPoint = '.',
        triggerAtEnter = null,
        triggerAtInput = null,
        nonKeyboardEvent = null,
    }) {
        const component = Component.current;
        const state = { buffer: '' };

        function updateBuffer(input) {
            const isEmpty = val => {
                return val === '' || val === null;
            };
            let isFirstInput = isEmpty(state.buffer);
            if (input === decimalPoint) {
                if (isFirstInput) {
                    state.buffer = '0.';
                } else if (!state.buffer.length || state.buffer === '-') {
                    state.buffer += '0.';
                } else if (state.buffer.indexOf(decimalPoint) < 0) {
                    state.buffer = state.buffer + decimalPoint;
                }
            } else if (input === 'CLEAR') {
                state.buffer = isEmpty(state.buffer) ? null : '';
            } else if (input === 'BACKSPACE') {
                state.buffer = isEmpty(state.buffer)
                    ? null
                    : state.buffer.substring(0, state.buffer.length - 1);
            } else if (input === '+') {
                if (state.buffer[0] === '-') {
                    state.buffer = state.buffer.substring(1, state.buffer.length);
                }
            } else if (input === '-') {
                if (isFirstInput) {
                    state.buffer = '-0';
                } else if (state.buffer[0] === '-') {
                    state.buffer = state.buffer.substring(1, state.buffer.length);
                } else {
                    state.buffer = '-' + state.buffer;
                }
            } else if (!isNaN(parseInt(input, 10))) {
                if (isFirstInput) {
                    state.buffer = '' + input;
                } else {
                    state.buffer += input;
                }
            }
            if (state.buffer === '-') {
                state.buffer = '';
            }
        }

        function getInput(key) {
            if (key === '.' || key === ',') {
                return decimalPoint;
            } else if ('0123456789+-'.includes(key)) {
                return key;
            } else if (key === 'Delete') {
                return 'CLEAR';
            } else if (key === 'Backspace') {
                return 'BACKSPACE';
            }
        }

        function triggerEvents(key) {
            const input = getInput(key);
            if (key === 'Enter' && triggerAtEnter) {
                component.trigger(triggerAtEnter, state);
            } else if (input !== '' && triggerAtInput) {
                component.trigger(triggerAtInput, state);
            }
        }

        function onKeyboardInput(event) {
            const input = getInput(event.key);
            updateBuffer(input);
            event.preventDefault();
            triggerEvents(event.key);
        }

        function onNonKeyboardInput(event) {
            const input = getInput(event.detail.key);
            updateBuffer(input);
            event.preventDefault();
            triggerEvents(event.detail.key);
        }

        useExternalListener(window, 'keyup', onKeyboardInput);
        if (typeof nonKeyboardEvent === 'string') {
            useListener(nonKeyboardEvent, onNonKeyboardInput);
        }

        return {
            get() {
                return state.buffer;
            },
            reset() {
                state.buffer = '';
            },
            getThenReset() {
                const buffer = state.buffer;
                reset();
                return buffer;
            },
            set(val) {
                state.buffer = !isNaN(parseFloat(val)) ? val : '';
            },
        };
    }

    return { useNumberBuffer };
});
