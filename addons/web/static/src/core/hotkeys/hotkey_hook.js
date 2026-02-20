import { useLayoutEffect } from "@web/owl2/utils";
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
    useLayoutEffect(
        () => hotkeyService.add(hotkey, callback, options),
        () => []
    );
}
