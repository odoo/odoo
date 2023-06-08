/* @odoo-module */

import { Dropzone } from "@mail/core/common/dropzone";

import { useEffect, useExternalListener } from "@odoo/owl";

import { registry } from "@web/core/registry";

const componentRegistry = registry.category("main_components");

let id = 1;
export function useDropzone(targetRef, onDrop, extraClass) {
    const dropzoneId = `mail.dropzone_${id++}`;
    let dragCount = 0;
    let hasTarget = false;

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
        const shouldDisplayDropzone = dragCount && hasTarget;
        const hasDropzone = componentRegistry.contains(dropzoneId);
        if (shouldDisplayDropzone && !hasDropzone) {
            componentRegistry.add(dropzoneId, {
                Component: Dropzone,
                props: { extraClass, onDrop, ref: targetRef },
            });
        }
        if (!shouldDisplayDropzone && hasDropzone) {
            componentRegistry.remove(dropzoneId);
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
