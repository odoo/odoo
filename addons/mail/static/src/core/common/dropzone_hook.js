/* @odoo-module */

import { Dropzone } from "@mail/core/common/dropzone";

import { useEffect, useExternalListener } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export function useDropzone(targetRef, onDrop, extraClass, isDropzoneEnabled = () => true) {
    let dragCount = 0;
    let hasTarget = false;
    let removeDropzone = null;

    const overlay = useService("overlay");
    useExternalListener(document, "dragenter", onDragEnter);
    useExternalListener(document, "dragleave", onDragLeave);
    // Prevents the browser to open or download the file when it is dropped
    // outside of the dropzone.
    useExternalListener(window, "dragover", (ev) => ev.preventDefault());
    useExternalListener(window, "drop", (ev) => {
        ev.preventDefault();
        dragCount = 0;
        updateDropzone();
    });

    function updateDropzone() {
        const shouldDisplayDropzone = dragCount && hasTarget && isDropzoneEnabled();
        if (shouldDisplayDropzone && !removeDropzone) {
            removeDropzone = overlay.add(Dropzone, { extraClass, onDrop, ref: targetRef });
        }
        if (!shouldDisplayDropzone && removeDropzone) {
            removeDropzone();
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
