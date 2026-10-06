import { useCustomDropzone } from "@web/core/dropzone/dropzone_hook";
import { UploadDropzone } from "@web/core/dropzone/upload_dropzone";
import { useService } from "@web/core/utils/hooks";

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
                return action.currentController?.displayName;
            },
            onDrop: (files) =>
                handleViewButton({ clickParams: getButton().clickParams, getResParams, files }),
        },
        () => !!getButton()
    );
}

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
