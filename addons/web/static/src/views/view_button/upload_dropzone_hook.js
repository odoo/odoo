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
                button.display === "always" &&
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
