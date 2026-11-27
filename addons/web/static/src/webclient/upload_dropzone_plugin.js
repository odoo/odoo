import { Plugin, usePlugin } from "@odoo/owl";
import { DropzonePlugin } from "@web/core/dropzone/dropzone_plugin";
import { GlobalBusPlugin } from "@web/core/global_bus_plugin";
import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { services } from "@web/core/services";
import { uploadButtons } from "@web/views/view_button/view_button";
import { ActionPlugin, clearUncommittedChanges } from "@web/webclient/actions/action_plugin";

/**
 * Adds a dropzone to the content of the view whose control panel has an upload
 * button (`<button type="upload"/>`): the dropped files are uploaded as if they
 * were picked after a click on the button.
 * `uploadWithButton` does the same for the other dropzones of upload buttons.
 */
export class UploadDropzonePlugin extends Plugin {
    #action = usePlugin(ActionPlugin);
    #bus = usePlugin(GlobalBusPlugin).bus;
    #notification = usePlugin(NotificationPlugin);

    setup() {
        const action = this.#action;
        usePlugin(DropzonePlugin).add(() => this.#getTarget(), {
            get label() {
                return action.currentController?.displayName;
            },
            onDrop: (files) => this.uploadWithButton(this.#getButton(), files),
        });
    }

    #getButton() {
        return document.querySelector(".o_control_panel [type='upload']");
    }

    #getTarget() {
        const content = this.#getButton()
            ?.closest(".o_control_panel")
            .parentElement.querySelector(":scope > .o_content");
        return content?.querySelector(".o_renderer") || content;
    }

    /**
     * Uploads the files as a click on the upload button `button` would, with
     * the given files instead of the picked ones.
     *
     * @param {HTMLElement} button a rendered `<button type="upload"/>`
     * @param {File[]} files
     */
    async uploadWithButton(button, files) {
        if (!button) {
            return;
        }
        // the unsaved changes of the view (e.g. an edited list row) are saved first, as on a click
        if (!(await clearUncommittedChanges(this.#bus))) {
            this.#notification.add(
                _t("The files were not uploaded: the changes could not be saved."),
                { type: "danger" }
            );
            return;
        }
        const { method, ...params } = uploadButtons.get(button).uploadParams;
        await this.#action.doActionButton(
            {
                ...params,
                type: "upload",
                name: method,
                onClose: () => this.#action.doAction("soft_reload"),
            },
            { files }
        );
    }
}

services.add(UploadDropzonePlugin);
