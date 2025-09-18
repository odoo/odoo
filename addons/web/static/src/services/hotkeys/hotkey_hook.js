// @ts-check

/** @module @web/services/hotkeys/hotkey_hook - useHotkey hook to register/unregister keyboard shortcuts with component lifecycle */

import { useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
/**
 * This hook will register/unregister the given registration
 * when the caller component will mount/unmount.
 *
 * @param {string} hotkey
 * @param {import("./hotkey_service").HotkeyCallback} callback
 * @param {import("./hotkey_service").HotkeyOptions} [options] additional options
 */
export function useHotkey(hotkey, callback, options = {}) {
    const hotkeyService = useService("hotkey");
    useEffect(
        () => hotkeyService.add(hotkey, callback, options),
        () => [],
    );
}
