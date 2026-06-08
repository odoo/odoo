import { useLayoutEffect } from "@web/owl2/utils";
import { Dropzone } from "@web/core/dropzone/dropzone";
import { useService } from "@web/core/utils/hooks";
import { useListener } from "@odoo/owl";

/**
 * @param {Ref} targetRef - Element on which to place the dropzone.
 * @param {Class} dropzoneComponent - Class used to instantiate the dropzone component.
 * @param {Object} dropzoneComponentProps - Props given to the instantiated dropzone component.
 * @param {function} isDropzoneEnabled - Function that determines whether the dropzone should be enabled.
 */
export function useCustomDropzone(
    targetRef,
    dropzoneComponent,
    dropzoneComponentProps,
    isDropzoneEnabled = () => true
) {
    const overlayService = useService("overlay");
    const uiService = useService("ui");

    // Transitional shim: accept both an Owl 3 signal ref (call it to get the
    // element) and a legacy `.el` ref object. Remove once all callers pass a signal.
    // Note: `useChildRef()` returns a *function* with an `.el` getter, so we must
    // probe `.el` first and only fall back to calling the ref when no `.el` is
    // exposed at all (true signal refs).
    const getTargetEl = () => ("el" in targetRef ? targetRef.el : targetRef());

    let dragCount = 0;
    let hasTarget = false;
    let removeDropzone = false;

    useListener(document, "dragenter", onDragEnter, { capture: true });
    useListener(document, "dragleave", onDragLeave, { capture: true });
    // Prevents the browser to open or download the file when it is dropped
    // outside of the dropzone.
    useListener(window, "dragover", (ev) => {
        if (ev.dataTransfer && ev.dataTransfer.types.includes("Files")) {
            ev.preventDefault();
        }
    });
    useListener(
        window,
        "drop",
        (ev) => {
            if (ev.dataTransfer && ev.dataTransfer.types.includes("Files")) {
                ev.preventDefault();
            }
            dragCount = 0;
            updateDropzone();
        },
        { capture: true }
    );

    function updateDropzone() {
        const hasDropzone = !!removeDropzone;
        const isTargetInActiveElement = uiService.activeElement.contains(getTargetEl());
        const shouldDisplayDropzone =
            dragCount && hasTarget && isTargetInActiveElement && isDropzoneEnabled();

        if (shouldDisplayDropzone && !hasDropzone) {
            removeDropzone = overlayService.add(dropzoneComponent, {
                ref: targetRef,
                ...dropzoneComponentProps,
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

    useLayoutEffect(
        (el) => {
            hasTarget = !!el;
            updateDropzone();
        },
        () => [getTargetEl()]
    );
}

/**
 * @param {Ref} targetRef - Element on which to place the dropzone.
 * @param {function} onDrop - Callback function called when the user drops a file on the dropzone.
 * @param {string} extraClass - Classes that will be added to the standard `Dropzone` component.
 * @param {function} isDropzoneEnabled - Function that determines whether the dropzone should be enabled.
 */
export function useDropzone(targetRef, onDrop, extraClass, isDropzoneEnabled = () => true) {
    const dropzoneComponent = Dropzone;
    const dropzoneComponentProps = { extraClass, onDrop };
    useCustomDropzone(targetRef, dropzoneComponent, dropzoneComponentProps, isDropzoneEnabled);
}
