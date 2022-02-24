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
 * @param {boolean} [options.bypassEditableProtection=false]
 *  if true the hotkey service will call this registration
 *  even if an editable element is focused
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
