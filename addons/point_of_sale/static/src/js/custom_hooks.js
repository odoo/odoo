odoo.define('point_of_sale.custom_hooks', function(require) {
    'use strict';

    const { Component, hooks } = owl;
    const { useExternalListener } = hooks;
    const { useListener } = require('web.custom_hooks');
    const { BarcodeEvents } = require('barcodes.BarcodeEvents');

    /**
     * When this hook is used inside a component, a keyup listener is started
     * in window. If the input is not from barcode or the input is not happening
     * inside an editable (`input` or `textarea`) elements, then, any valid
     * number input will be intercepted and registered to the buffer inside this
     * hook.
     *
     * When `Enter` key is pressed, the component's `triggerAtEnter` event
     * is triggered.
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
     * @param {String} obj.nonKeyboardEvent Event to trigger when input from other event
     *      that is different from keyup occurs.
     *      e.g. Clicking a numpad button can trigger an event and if it triggered
     *          `nonKeyboardEvent` then that event is intercepted here via
     *          `onNonKeyboardInput`. The event should carry a payload { key } that will
     *          be checked and used as input to the buffer.
     * @param {Integer} obj.maxTimeBetweenKeys Barcode's max time between keys in ms.
     *
     * @return {Object} object with the following methods
     *      - get(): returns the recent value of the buffer.
     *      - set(valStr): sets `valStr` as value of the buffer.
     *      - reset(): set the buffer to empty string.
     *      - pause(): pauses the recording of buffer
     *      - resume(): resume on recording number buffer
     */
    function useNumberBuffer({
        decimalPoint = '.',
        triggerAtEnter = null,
        triggerAtInput = null,
        nonKeyboardEvent = null,
        maxTimeBetweenKeys = BarcodeEvents.max_time_between_keys_in_ms,
    }) {
        // used for triggering events on the component
        const component = Component.current;

        // contains the number buffer
        const state = { buffer: '' };

        // Needed to monitor fast inputs.
        // We want to limit speed of input. Useful for
        // taking into account barcode input.
        let eventsBuffer = [];
        let timeout = null;

        // for pausing the mutation of buffer
        let isPaused = false;

        // Responsible for mutating the buffer based on valid input.
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

        // Takes `key` from details of the event
        // and converts it to something understandable
        // by `updateBuffer` function.
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

        // Before actually processing the input, we want to make sure
        // that it is not coming from very fast input such as barcode.
        // Thus, we wrap the real event handler with this function.
        // It buffers input events based on the `maxTimeBetweenKeys`.
        // When the `handler` is ready to execute, we check in the
        // event handler if we are really interested on buffering the
        // keys from the buffered events.
        function bufferEvents(handler) {
            return event => {
                if (['INPUT', 'TEXTAREA'].includes(event.target.tagName)) return;
                clearTimeout(timeout);
                eventsBuffer.push(event);
                timeout = setTimeout(handler, maxTimeBetweenKeys);
            };
        }

        function onKeyboardInput() {
            if (eventsBuffer.length === 1 && !isPaused) {
                const event = eventsBuffer[0];
                const input = getInput(event.key);
                updateBuffer(input);
                event.preventDefault();
                triggerEvents(event.key);
            }
            eventsBuffer = [];
        }

        function onNonKeyboardInput() {
            if (eventsBuffer.length === 1 && !isPaused) {
                const event = eventsBuffer[0];
                const input = getInput(event.detail.key);
                updateBuffer(input);
                event.preventDefault();
                triggerEvents(event.detail.key);
            }
            eventsBuffer = [];
        }

        useExternalListener(window, 'keyup', bufferEvents(onKeyboardInput));
        if (typeof nonKeyboardEvent === 'string') {
            useListener(nonKeyboardEvent, bufferEvents(onNonKeyboardInput));
        }

        return {
            pause() {
                isPaused = true;
            },
            resume() {
                isPaused = false;
            },
            get() {
                return state.buffer;
            },
            reset() {
                state.buffer = '';
            },
            set(val) {
                state.buffer = !isNaN(parseFloat(val)) ? val : '';
            },
        };
    }

    return { useNumberBuffer };
});
