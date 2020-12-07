/** @odoo-module alias=point_of_sale.custom_hooks **/

const { Component } = owl;
const { onMounted, onPatched, onWillUnmount } = owl.hooks;

function useAutoFocusToLast() {
    const current = Component.current;
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

function useBarcodeReader(barcodeReader, callbackMap, exclusive = false) {
    const current = Component.current;
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

export default { useAutoFocusToLast, useBarcodeReader };
