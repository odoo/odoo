import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { HtmlField } from "@html_editor/fields/html_field";

patch(HtmlField.prototype, {
    onEditorLoad(editor) {
        super.onEditorLoad(editor);
        window.__html_field_editor_for_tour = editor;
    },
});

const PNG_PIXEL_BASE64 =
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";
const PASTED_FILE_NAME = "pending.png";

function base64ToFile(base64, name, type) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return new File([bytes], name, { type });
}

function pasteImage() {
    const editable = document.querySelector(".odoo-editor-editable");
    editable.focus();
    const range = document.createRange();
    range.selectNodeContents(editable);
    range.collapse(false);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);

    const file = base64ToFile(PNG_PIXEL_BASE64, PASTED_FILE_NAME, "image/png");
    const clipboardData = new DataTransfer();
    clipboardData.items.add(file);
    editable.dispatchEvent(
        new ClipboardEvent("paste", { clipboardData, bubbles: true, cancelable: true })
    );
}

function openMediaDialog() {
    window.__html_field_editor_for_tour.shared.media.openMediaDialog();
}

registry.category("web_tour.tours").add("html_field_pending_attachments_same_record_tour", {
    steps: () => [
        { content: "Wait for the html editor", trigger: ".odoo-editor-editable" },
        { content: "Focus the editable", trigger: ".odoo-editor-editable", run: "click" },
        { content: "Paste a base64 image", trigger: ".odoo-editor-editable", run: pasteImage },
        {
            content: "Wait for the base64 image",
            trigger: `.odoo-editor-editable img.o_b64_image_to_save`,
        },
        { content: "Save the record", trigger: ".o_form_button_save", run: "click" },
        { content: "Wait until save is done", trigger: ".o_form_button_save:not(:visible)" },
        {
            content: "Wait until the saved image src is no longer base64",
            trigger: `.odoo-editor-editable img:not([src^="data:"])`,
        },
        {
            content: "Reopen the media dialog",
            trigger: ".odoo-editor-editable",
            run: openMediaDialog,
        },
        {
            content: "Verify the pasted attachment is listed in the saved record's dialog",
            trigger: `.o_select_media_dialog button[aria-label="${PASTED_FILE_NAME}"]`,
        },
    ],
});

registry.category("web_tour.tours").add("html_field_pending_attachments_other_record_tour", {
    steps: () => [
        { content: "Wait for the html editor", trigger: ".odoo-editor-editable" },
        { content: "Focus the editable", trigger: ".odoo-editor-editable", run: "click" },
        { content: "Paste a base64 image", trigger: ".odoo-editor-editable", run: pasteImage },
        {
            content: "Wait for the base64 image",
            trigger: `.odoo-editor-editable img.o_b64_image_to_save`,
        },
        { content: "Save the record", trigger: ".o_form_button_save", run: "click" },
        { content: "Wait until save is done", trigger: ".o_form_button_save:not(:visible)" },
        {
            content: "Wait until the saved image src is no longer base64",
            trigger: `.odoo-editor-editable img:not([src^="data:"])`,
        },
        { content: "Create a new record", trigger: ".o_form_button_create", run: "click" },
        {
            content: "Wait for the editable to remount on the new record",
            trigger: `.odoo-editor-editable:not(:has(img))`,
        },
        {
            content: "Open media dialog on the new record",
            trigger: ".odoo-editor-editable",
            run: openMediaDialog,
        },
        {
            content: "Wait for the dialog body to render",
            trigger: ".o_select_media_dialog .modal-body",
        },
        {
            content: "Verify the previous record's attachment is not listed",
            trigger: ".o_select_media_dialog .modal-body",
            async run() {
                await new Promise((resolve) => setTimeout(resolve, 500));
                const found = document.querySelector(
                    `.o_select_media_dialog button[aria-label="${PASTED_FILE_NAME}"]`
                );
                if (found) {
                    throw new Error(
                        `${PASTED_FILE_NAME} should not appear in another new record's dialog`
                    );
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("html_field_pending_attachments_discard_tour", {
    steps: () => [
        { content: "Wait for the html editor", trigger: ".odoo-editor-editable" },
        { content: "Focus the editable", trigger: ".odoo-editor-editable", run: "click" },
        { content: "Paste a base64 image", trigger: ".odoo-editor-editable", run: pasteImage },
        {
            content: "Wait for the base64 image",
            trigger: `.odoo-editor-editable img.o_b64_image_to_save`,
        },
        {
            content: "Blur the editor by clicking the char input",
            trigger: ".o_field_widget[name=char] input",
            run: "click",
        },
        {
            content: "Wait until the pasted image has been converted to an attachment",
            trigger: `.odoo-editor-editable img:not([src^="data:"])`,
        },
        { content: "Discard the record", trigger: ".o_form_button_cancel", run: "click" },
        {
            content: "Wait for the form view to be torn down after discard",
            trigger: "body:not(:has(.o_form_view))",
        },
    ],
});
