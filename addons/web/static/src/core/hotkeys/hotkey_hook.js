/** @odoo-module **/

import { useEffect, useService } from "@web/core/utils/hooks";

/**
 * This hook will register/unregister the given registration
 * when the caller component will mount/unmount.
 *
 * @param {string} hotkey
 * @param {()=>void} callback
 * @param {Object} options additional options
 * @param {boolean} [options.allowRepeat=false]
 *  allow registration to perform multiple times when hotkey is held down
 * @param {boolean} [options.capture=false]
 *  registrations in capture mode would get called beforehand and would
 *  have the opportunity to stop the dispatching of an hotkey by
 *  returning an object `{captured: true}` in order to cancel current dispatching.
 *  Note that the capturer may be asynchronous and could delay the dispatching.
 * @param {boolean} [options.global=false]
 *  allow registration to perform no matter the UI active element
 */
export function useHotkey(hotkey, callback, options = {}) {
    const hotkeyService = useService("hotkey");
    useEffect(
        () => hotkeyService.add(hotkey, callback, options),
        () => []
    );
}
