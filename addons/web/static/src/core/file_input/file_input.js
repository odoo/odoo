import { useRef } from "@web/owl2/utils";
import { Component, onMounted, props, proxy, t } from "@odoo/owl";
import { useFileUploader } from "@web/core/utils/files";

/**
 * Custom file input
 *
 * Component representing a customized input of type file. It takes a sub-template
 * in its default t-slot and uses it as the trigger to open the file upload
 * prompt.
 * @extends Component
 *
 * Props:
 * @param {string} [props.acceptedFileExtensions='*'] Comma-separated
 *      list of authorized file extensions (default to all).
 * @param {string} [props.route='/web/binary/upload'] Route called when
 *      a file is uploaded in the input.
 * @param {string} [props.resId]
 * @param {string} [props.resModel]
 * @param {string} [props.multiUpload=false] Whether the input should allow
 *      to upload multiple files at once.
 */
export class FileInput extends Component {
    static template = "web.FileInput";
    props = props({
        acceptedFileExtensions: t.string().optional("*"),
        autoOpen: t.boolean().optional(),
        hidden: t.boolean().optional(false),
        multiUpload: t.boolean().optional(false),
        onUpload: t.function().optional(() => () => {}),
        onWillUploadFiles: t.function().optional(),
        beforeOpen: t.function().optional(() => async () => true),
        resId: t.number().optional(),
        resModel: t.string().optional(),
        route: t.string().optional("/web/binary/upload_attachment"),
    });

    setup() {
        this.uploadFiles = useFileUploader();
        this.fileInputRef = useRef("file-input");
        this.state = proxy({
            // Disables upload button if currently uploading.
            isDisable: false,
        });

        onMounted(() => {
            if (this.props.autoOpen) {
                this.onTriggerClicked();
            }
        });
    }

    get httpParams() {
        const { resId, resModel } = this.props;
        const params = {
            csrf_token: odoo.csrf_token,
            ufile: [...this.fileInputRef.el.files],
        };
        if (resModel) {
            params.model = resModel;
        }
        if (resId !== undefined) {
            params.id = resId;
        }
        return params;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Upload an attachment to the given route with the given parameters:
     * - ufile: list of files contained in the file input
     * - csrf_token: CSRF token provided by the odoo global object
     * - resModel: a specific model which will be given when creating the attachment
     * - resId: the id of the resModel target instance
     */
    async onFileInputChange() {
        this.state.isDisable = true;
        const httpParams = this.httpParams;
        if (this.props.onWillUploadFiles) {
            try {
                const files = await this.props.onWillUploadFiles(httpParams.ufile);
                httpParams.ufile = files;
            } catch (e) {
                this.state.isDisable = false;
                throw e;
            }
        }
        const parsedFileData = await this.uploadFiles(this.props.route, httpParams);
        if (parsedFileData) {
            // When calling onUpload, also pass the files to allow to get data like their names
            this.props.onUpload(
                parsedFileData,
                this.fileInputRef.el ? this.fileInputRef.el.files : []
            );
            // Because the input would not trigger this method if the same file name is uploaded,
            // we must clear the value after handling the upload
            this.fileInputRef.el.value = null;
        }
        this.state.isDisable = false;
    }

    /**
     * Redirect clicks from the trigger element to the input.
     */
    async onTriggerClicked() {
        if (await this.props.beforeOpen()) {
            this.fileInputRef.el.click();
        }
    }
}
