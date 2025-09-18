// @ts-check

/** @module @web/components/dropzone/dropzone_hook - Hooks for attaching drag-and-drop file upload zones to DOM elements */

import { useEffect, useExternalListener } from "@odoo/owl";
import { Dropzone } from "@web/components/dropzone/dropzone";
import { useService } from "@web/core/utils/hooks";
/**
 * @param {any} targetRef - Element on which to place the dropzone.
 * @param {typeof import("@odoo/owl").Component} dropzoneComponent - Class used to instantiate the dropzone component.
 * @param {Object} dropzoneComponentProps - Props given to the instantiated dropzone component.
 * @param {function} isDropzoneEnabled - Function that determines whether the dropzone should be enabled.
 */
export function useCustomDropzone(
    targetRef,
    dropzoneComponent,
    dropzoneComponentProps,
    isDropzoneEnabled = () => true,
) {
    const overlayService = useService("overlay");
    const uiService = useService("ui");

    let dragCount = 0;
    let hasTarget = false;
    /** @type {false|(() => void)} */
    let removeDropzone = false;

    useExternalListener(document, "dragenter", onDragEnter, { capture: true });
    useExternalListener(document, "dragleave", onDragLeave, { capture: true });
    // Prevents the browser to open or download the file when it is dropped
    // outside of the dropzone.
    useExternalListener(window, "dragover", (ev) => {
        if (ev.dataTransfer && ev.dataTransfer.types.includes("Files")) {
            ev.preventDefault();
        }
    });
    useExternalListener(
        window,
        "drop",
        (ev) => {
            if (ev.dataTransfer && ev.dataTransfer.types.includes("Files")) {
                ev.preventDefault();
            }
            dragCount = 0;
            updateDropzone();
        },
        { capture: true },
    );

    function updateDropzone() {
        const hasDropzone = !!removeDropzone;
        const isTargetInActiveElement = uiService.activeElement.contains(targetRef.el);
        const shouldDisplayDropzone =
            !!dragCount && hasTarget && isTargetInActiveElement && isDropzoneEnabled();

        if (shouldDisplayDropzone && !hasDropzone) {
            removeDropzone = overlayService.add(dropzoneComponent, {
                ref: targetRef,
                ...dropzoneComponentProps,
            });
        }
        if (!shouldDisplayDropzone && hasDropzone) {
            /** @type {any} */ (removeDropzone)();
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
        () => [targetRef.el],
    );
}

/**
 * @param {any} targetRef - Element on which to place the dropzone.
 * @param {function} onDrop - Callback function called when the user drops a file on the dropzone.
 * @param {string} extraClass - Classes that will be added to the standard `Dropzone` component.
 * @param {function} isDropzoneEnabled - Function that determines whether the dropzone should be enabled.
 */
export function useDropzone(
    targetRef,
    onDrop,
    extraClass,
    isDropzoneEnabled = () => true,
) {
    const dropzoneComponent = Dropzone;
    const dropzoneComponentProps = { extraClass, onDrop };
    useCustomDropzone(
        targetRef,
        dropzoneComponent,
        dropzoneComponentProps,
        isDropzoneEnabled,
    );
}
