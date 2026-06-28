import { onMounted, onWillUnmount } from "@odoo/owl";
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
    let cleanup;
    onMounted(() => {
        cleanup = hotkeyService.add(hotkey, callback, options);
    });
    onWillUnmount(() => cleanup());
}
