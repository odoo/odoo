/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { multiFileUpload } from "@sign/backend_components/multi_file_upload";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { TemplateAlertDialog } from "@sign/backend_components/template_alert_dialog/template_alert_dialog";
import { onWillStart, useComponent, useRef } from "@odoo/owl";

export function useSignViewButtons() {
    const component = useComponent();
    const fileInput = useRef("uploadFileInput");
    const user = useService("user");
    const orm = useService("orm");
    const dialog = useService("dialog");
    const action = useService("action");

    onWillStart(async () => {
        component.isSignUser = await user.hasGroup("sign.group_sign_user");
    });

    let latestRequestContext;
    let inactive;

    const uploadFile = async (file) => {
        const dataUrl = await getDataURLFromFile(file);
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
            },
        });
    };

    return {
        /**
         * Handles the template file upload logic.
         */
        onFileInputChange: async (ev) => {
            if (!ev.target.files.length) {
                return;
            }
            const files = ev.target.files;
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
         * Opens the file input dialog and sets the given properties
         * for the file upload.
         */
        requestFile(active, context) {
            inactive = !active;
            latestRequestContext = context;
            fileInput.el.click();
        },
    };
}
