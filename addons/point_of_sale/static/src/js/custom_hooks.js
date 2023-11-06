odoo.define('point_of_sale.custom_hooks', function (require) {
    'use strict';

    const { onMounted, onPatched, onWillUnmount, useComponent, useRef } = owl;
    const { escapeRegExp } = require('@web/core/utils/strings');

    /**
     * Introduce error handlers in the component.
     *
     * IMPROVEMENT: This is a terrible hook. There could be a better way to handle
     * the error when the order failed to sync.
     */
    function useErrorHandlers() {
        const component = useComponent();

        component._handlePushOrderError = async function (error) {
            // This error handler receives `error` equivalent to `error.message` of the rpc error.
            if (error.message === 'Backend Invoice') {
                await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Please print the invoice from the backend'),
                    body:
                        this.env._t(
                            'The order has been synchronized earlier. Please make the invoice from the backend for the order: '
                        ) + error.data.order.name,
                });
            } else if (error.code < 0) {
                // XmlHttpRequest Errors
                const title = this.env._t('Unable to sync order');
                const body = this.env._t(
                    'Check the internet connection then try to sync again by clicking on the red wifi button (upper right of the screen).'
                );
                await this.showPopup('OfflineErrorPopup', { title, body });
            } else if (error.code === 200) {
                // OpenERP Server Errors
                await this.showPopup('ErrorTracebackPopup', {
                    title: error.data.message || this.env._t('Server Error'),
                    body:
                        error.data.debug ||
                        this.env._t('The server encountered an error while receiving your order.'),
                });
            } else if (error.code === 700) {
                // Sweden Fiscal module errors
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Fiscal data module error'),
                    body:
                        error.data.error.status ||
                        this.env._t('The fiscal data module encountered an error while receiving your order.'),
                });
            } else if (error.code === 701) {
                // Belgian Fiscal module errors
                let bodyMessage = "";
                if(error.error.errorCode)
                    bodyMessage = "'" + error.error.errorCode + "': " + error.error.errorMessage;
                else
                    bodyMessage = "Fiscal data module is not on.";
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Fiscal data module error'),
                    body: bodyMessage
                });
            } else {
                // ???
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Unknown Error'),
                    body: this.env._t(
                        'The order could not be sent to the server due to an unknown error'
                    ),
                });
            }
        };
    }

    function useAutoFocusToLast() {
        const current = useComponent();
        let target = null;
        function autofocus() {
            const prevTarget = target;
            const allInputs = current.el.querySelectorAll('input');
            target = allInputs[allInputs.length - 1];
            if (target && target !== prevTarget) {
                target.focus();
                target.selectionStart = target.selectionEnd = target.value.length;
            }
        }
        onMounted(autofocus);
        onPatched(autofocus);
    }

    function useBarcodeReader(callbackMap, exclusive = false) {
        const current = useComponent();
        const barcodeReader = current.env.barcode_reader;
        for (let [key, callback] of Object.entries(callbackMap)) {
            callbackMap[key] = callback.bind(current);
        }
        onMounted(() => {
            if (barcodeReader) {
                for (let key in callbackMap) {
                    if (exclusive) {
                        barcodeReader.set_exclusive_callback(key, callbackMap[key]);
                    } else {
                        barcodeReader.set_action_callback(key, callbackMap[key]);
                    }
                }
            }
        });
        onWillUnmount(() => {
            if (barcodeReader) {
                for (let key in callbackMap) {
                    if (exclusive) {
                        barcodeReader.remove_exclusive_callback(key, callbackMap[key]);
                    } else {
                        barcodeReader.remove_action_callback(key, callbackMap[key]);
                    }
                }
            }
        });
    }

    function useValidateCashInput(inputRef, startingValue) {
        const cashInput = useRef(inputRef);
        const current = useComponent();
        const decimalPoint = current.env._t.database.parameters.decimal_point;
        const thousandsSep = current.env._t.database.parameters.thousands_sep;
        // Replace the thousands separator and decimal point with regex-escaped versions
        const escapedDecimalPoint = escapeRegExp(decimalPoint);
        let floatRegex;
        if (thousandsSep) {
            const escapedThousandsSep = escapeRegExp(thousandsSep);
            floatRegex = new RegExp(`^-?(?:\\d+(${escapedThousandsSep}\\d+)*)?(?:${escapedDecimalPoint}\\d*)?$`);
        } else {
            floatRegex = new RegExp(`^-?(?:\\d+)?(?:${escapedDecimalPoint}\\d*)?$`);
        }
        function isValidFloat(inputValue) {
            return ![decimalPoint, '-'].includes(inputValue) && floatRegex.test(inputValue);
        }
        function handleCashInputChange(event) {
            let inputValue = (event.target.value || "").trim();

            // Check if the current input value is a valid float
            if (!isValidFloat(inputValue)) {
                event.target.classList.add('invalid-cash-input');
            } else {
                event.target.classList.remove('invalid-cash-input');
            }
        }

        onMounted(() => {
            if (cashInput.el) {
                cashInput.el.value = (startingValue || 0).toString().replace('.', decimalPoint);
                cashInput.el.addEventListener("input", handleCashInputChange);
            }
        });

        onWillUnmount(() => {
            if (cashInput.el) {
                cashInput.el.removeEventListener("input", handleCashInputChange);
            }
        })
    }

    function useAsyncLockedMethod(method) {
        const component = useComponent();
        let called = false;
        return async (...args) => {
            if (called) {
                return;
            }
            try {
                called = true;
                await method.call(component, ...args);
            } finally {
                called = false;
            }
        };
    }

    return { useErrorHandlers, useAutoFocusToLast, useBarcodeReader, useValidateCashInput, useAsyncLockedMethod };
});
