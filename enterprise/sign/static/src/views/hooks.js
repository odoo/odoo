/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService, useBus } from "@web/core/utils/hooks";
import { multiFileUpload } from "@sign/backend_components/multi_file_upload";
import { user } from "@web/core/user";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { TemplateAlertDialog } from "@sign/backend_components/template_alert_dialog/template_alert_dialog";
import { onWillStart, useComponent, useRef, useEnv } from "@odoo/owl";

export function useSignViewButtons() {
    const component = useComponent();
    const fileInput = useRef("uploadFileInput");
    const orm = useService("orm");
    const dialog = useService("dialog");
    const action = useService("action");
    const env = useEnv();

    onWillStart(async () => {
        component.isSignUser = await user.hasGroup("sign.group_sign_user");
    });

    let latestRequestContext;
    let inactive;
    let resModel;

    const uploadFile = async (file) => {
        const dataUrl = await getDataURLFromFile(file);
        inactive = resModel === 'sign.template' ? true : false;
        const args = [file.name, dataUrl.split(",")[1], inactive];
        return await orm.call("sign.template", "create_with_attachment_data", args);
    };

    /**
     * Called on newly created templates, does a sign.Template action on those.
     */
    const handleTemplates = (templates) => {
        if (!templates || !templates.length) {
            return;
        }
        const file = templates.shift();
        multiFileUpload.addNewFiles(templates);
        action.doAction({
            type: "ir.actions.client",
            tag: "sign.Template",
            name: _t("Template %s", file.name),
            params: {
                sign_edit_call: latestRequestContext,
                id: file.template,
                sign_directly_without_mail: false,
                resModel: resModel,
            },
        });
    };

    const upload = {
        /**
         * Handles the template file upload logic.
         */
        onFileInputChange: async (ev) => {
            const files = ev?.type === "change" ? ev.target.files : ev.detail.files;
            if (!files || !files.length) {
                return;
            }
            const uploadedTemplates = await Promise.all(Array.from(files).map(uploadFile));
            const templates = uploadedTemplates.map((template, index) => ({
                template,
                name: files[index].name,
            }));
            const { true: succesfulTemplates, false: failedTemplates } = templates.reduce(
                (result, item) => {
                    const key = Boolean(item.template);
                    if (!result[key]) {
                        result[key] = [];
                    }
                    result[key].push(item);
                    return result;
                },
                {}
            );
            if (failedTemplates && failedTemplates.length) {
                dialog.add(TemplateAlertDialog, {
                    title: _t("File Error"),
                    failedTemplates,
                    successTemplateCount: succesfulTemplates && succesfulTemplates.length,
                    confirm: handleTemplates.bind(undefined, succesfulTemplates),
                });
            } else {
                handleTemplates(succesfulTemplates);
            }
            ev.target.value = "";
        },

        /**
        * Initiates the file upload process by opening a file input dialog
        * and configuring the 'save as template' button based on the provided model
        * and other properties.
        *
        * @param {Object}
        */
        requestFile(context) {
            latestRequestContext = context;
            resModel = this.props.resModel;
            fileInput.el.click();
        },
    };

    useBus(env.bus, "change_file_input", async (ev) => {
        if (component.constructor.name === 'SignActionHelper') {
            // Skip processing in SignActionHelper(signRenderer) call to prevent double handling
            // because its triggered from signController too.
            return;
        }
        fileInput.el.files = ev.detail.files;
        resModel = ev.detail.resModel;
        await upload.onFileInputChange(ev);
    });

    return upload
}
