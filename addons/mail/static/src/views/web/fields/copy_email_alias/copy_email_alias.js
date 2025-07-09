import { registry } from "@web/core/registry";
import {
    CopyClipboardButtonField,
    copyClipboardButtonField,
} from "@web/views/fields/copy_clipboard/copy_clipboard_field";

export class EmailAliasCopyClipboardButtonField extends CopyClipboardButtonField {
    static template = "web.EmailAliasCopyClipboardButtonField";
}

export const emailAliasCopyClipboardButtonField = {
    ...copyClipboardButtonField,
    component: EmailAliasCopyClipboardButtonField,
};

registry
    .category("fields")
    .add("EmailAliasCopyClipboardButtonField", emailAliasCopyClipboardButtonField);
