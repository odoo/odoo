import { useService } from "@web/core/utils/hooks";

export function useSingleDialog() {
    let close = null;
    const dialog = useService("dialog");
    return {
        open(dialogClass, props) {
            // If the dialog is already open, we don't want to open a new one
            if (!close) {
                close = dialog.add(dialogClass, props, {
                    onClose: () => {
                        close = null;
                    },
                });
            }
        },
        close() {
            close?.();
        },
    };
}
