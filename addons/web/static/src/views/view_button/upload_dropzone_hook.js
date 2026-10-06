import { useCustomDropzone } from "@web/core/dropzone/dropzone_hook";
import { UploadDropzone } from "@web/core/dropzone/upload_dropzone";
import { useService } from "@web/core/utils/hooks";

/**
 * Shows a dropzone over the content of a multi-record view while files are
 * dragged, when the view has a visible `<button type="upload"/>`. Its label is
 * the `dropzone-label` of the button, or the name of the action. The files
 * are handled as if they were picked with the first of these buttons.
 *
 * @param {Object} params
 * @param {() => HTMLElement | undefined} params.getTargetEl the area to outline
 * @param {() => Object[]} params.getButtons the header buttons of the arch
 * @param {(modifier: string) => boolean} params.isInvisible
 * @param {() => Object} params.getResParams see `ViewButtonHandlerParams`
 * @param {import("./view_button_hook").ViewButtonHandler} params.handleViewButton
 */
export function useUploadDropzone({
    getTargetEl,
    getButtons,
    isInvisible,
    getResParams,
    handleViewButton,
}) {
    const action = useService("action");
    const getButton = () =>
        getButtons().find(
            (button) =>
                button.clickParams.type === "upload" &&
                ["always", "dropzone"].includes(button.display) &&
                !isInvisible(button.invisible)
        );
    useCustomDropzone(
        getTargetEl,
        UploadDropzone,
        {
            get label() {
                const button = getButton();
                return (
                    button &&
                    (button.clickParams["dropzone-label"] || action.currentController?.displayName)
                );
            },
            onDrop: (files) =>
                handleViewButton({ clickParams: getButton().clickParams, getResParams, files }),
        },
        () => !!getButton()
    );
}

/**
 * Shows a dropzone over a record (e.g. a kanban card) while files are dragged,
 * if it contains a visible `<button type="upload"/>`. The files are handled as
 * if they were picked with this button, for this record.
 *
 * @param {() => HTMLElement | null} getRecordEl
 * @param {() => string} getLabel label of the dropzone
 */
export function useRecordUploadDropzone(getRecordEl, getLabel) {
    const getButton = () =>
        [...(getRecordEl()?.querySelectorAll('button[type="upload"]') ?? [])].find(
            // `hidden`: a button with `options.dropzone_only` (see `ViewButton`)
            (button) => button.offsetParent || button.hidden
        );
    useCustomDropzone(
        getRecordEl,
        UploadDropzone,
        {
            get label() {
                return getLabel();
            },
            onDrop: (files) =>
                getButton()?.dispatchEvent(new CustomEvent("upload-files", { detail: { files } })),
        },
        () => !!getButton()
    );
}
