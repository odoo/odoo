odoo.define('point_of_sale.custom_hooks', function(require) {
    'use strict';

    const { Component, hooks } = owl;
    const { useExternalListener, useState } = hooks;
    const { useListener } = require('web.custom_hooks');
    const { BarcodeEvents } = require('barcodes.BarcodeEvents');
    const { parse } = require('web.field_utils');

    /**
     * This hook introduces a `numberBuffer` field in the current component.
     * The following functions (state) can be accessed to the `numberBuffer`
     * field:
     *      - get(): returns the recent value of the buffer.
     *      - set(valStr): sets `valStr` as value of the buffer.
     *      - reset(): set the buffer to empty string.
     *      - pause(): pauses the recording of buffer
     *      - resume(): resume on recording number buffer
     *      - state: contains the string buffer
     *
     * When this hook is activate in a component, a keyup listener is started
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
     *      /!\ Should be unique as this is assigned as listener to window.
     *      e.g. Clicking a numpad button can trigger an event and if it triggered
     *          `nonKeyboardEvent` then that event is intercepted here via
     *          `onNonKeyboardInput`. The event should carry a payload { key } that will
     *          be checked and used as input to the buffer.
     * @param {Integer} obj.maxTimeBetweenKeys Barcode's max time between keys in ms.
     *
     * @return {Object} object with the following methods

     */
    function useNumberBuffer({
        decimalPoint = null,
        triggerAtEnter = null,
        triggerAtInput = null,
        nonKeyboardEvent = null,
        maxTimeBetweenKeys = BarcodeEvents.max_time_between_keys_in_ms,
    }) {
        // used for triggering events on the component
        const component = Component.current;
        decimalPoint = decimalPoint || component.env._t.database.parameters.decimal_point;

        // contains the number buffer
        const state = useState({ buffer: '' });

        // Needed to monitor fast inputs.
        // We want to limit speed of input. Useful for
        // taking into account barcode input.
        let eventsBuffer = [];
        let timeout = null;

        // for pausing the mutation of buffer
        let isPaused = false;

        let isReset = false;

        // Responsible for mutating the buffer based on valid input.
        function updateBuffer(input) {
            const isEmpty = val => {
                return val === '' || val === null;
            };
            if (input === undefined || input === null) return;
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
                if (isReset) {
                    state.buffer = '';
                    isReset = false;
                    return;
                }
                state.buffer = isEmpty(state.buffer) ? null : '';
            } else if (input === 'BACKSPACE') {
                if (isReset) {
                    state.buffer = '';
                    isReset = false;
                    return;
                }
                const buffer = state.buffer;
                if (isEmpty(buffer)) {
                    state.buffer = null;
                } else {
                    const nCharToRemove = buffer[buffer.length - 1] === decimalPoint ? 2 : 1;
                    state.buffer = buffer.substring(0, buffer.length - nCharToRemove);
                }
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
            } else if (input[0] === '+' && !isNaN(parseFloat(input))) {
                // when input is like '+10', '+50', etc
                const inputValue = parse.float(input.slice(1));
                const currentBufferValue = parse.float(state.buffer);
                state.buffer = component.env.pos.formatFixed(inputValue + currentBufferValue);
            } else if (!isNaN(parseInt(input, 10))) {
                if (isFirstInput) {
                    state.buffer = '' + input;
                } else {
                    state.buffer += input;
                }
            }
            if (state.buffer === '-' || /^(0)\1+$/.test(state.buffer)) {
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
            } else if (key.length > 1 && key[0] === '+') {
                return key;
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
                // Ignore input if modifier key is pressed.
                if (
                    event instanceof KeyboardEvent &&
                    (event.getModifierState('Fn') ||
                        event.getModifierState('Hyper') ||
                        event.getModifierState('OS') ||
                        event.getModifierState('Super') ||
                        event.getModifierState('Win') ||
                        event.getModifierState('Control') ||
                        event.getModifierState('Alt'))
                ) {
                    return;
                }

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
                event.stopPropagation();
                triggerEvents(event.detail.key);
            }
            eventsBuffer = [];
        }

        useExternalListener(window, 'keyup', bufferEvents(onKeyboardInput));
        if (typeof nonKeyboardEvent === 'string') {
            useListener(nonKeyboardEvent, bufferEvents(onNonKeyboardInput));
        }

        component.numberBuffer = {
            state,
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
                isReset = true;
                state.buffer = '';
            },
            set(val) {
                state.buffer = !isNaN(parseFloat(val)) ? val : '';
            },
            getFloat() {
                return parse.float(this.get());
            },
        };
    }

    return { useNumberBuffer };
});
