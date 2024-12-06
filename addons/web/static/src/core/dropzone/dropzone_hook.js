import { Dropzone } from "@web/core/dropzone/dropzone";
import { useEffect, useExternalListener } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


export function useDropzone(targetRef, onDrop, extraClass, isDropzoneEnabled = () => true) {
    const overlayService = useService("overlay");
    const uiService = useService("ui");

    let dragCount = 0;
    let hasTarget = false;
    let removeDropzone = false;

    useExternalListener(document, "dragenter", onDragEnter, { capture: true });
    useExternalListener(document, "dragleave", onDragLeave, { capture: true });
    // Prevents the browser to open or download the file when it is dropped
    // outside of the dropzone.
    useExternalListener(window, "dragover", (ev) => ev.preventDefault());
    useExternalListener(window, "drop", (ev) => {
        ev.preventDefault();
        dragCount = 0;
        updateDropzone();
    }, { capture: true });

    function updateDropzone() {
        const hasDropzone = !!removeDropzone;
        const isTargetInActiveElement = uiService.activeElement.contains(targetRef.el);
        const shouldDisplayDropzone = dragCount && hasTarget && isTargetInActiveElement && isDropzoneEnabled();

        if (shouldDisplayDropzone && !hasDropzone) {
            removeDropzone = overlayService.add(Dropzone, {
                extraClass,
                onDrop,
                ref: targetRef
            });
        }
        if (!shouldDisplayDropzone && hasDropzone) {
            removeDropzone();
            removeDropzone = false;
        }
    }

    function onDragEnter(ev) {
        if (dragCount || (ev.dataTransfer && ev.dataTransfer.types.includes("Files"))) {
            dragCount++;
            updateDropzone();
        }
    }

    function onDragLeave() {
        if (dragCount) {
            dragCount--;
            updateDropzone();
        }
    }

    useEffect(
        (el) => {
            hasTarget = !!el;
            updateDropzone();
        },
        () => [targetRef.el]
    );
}
