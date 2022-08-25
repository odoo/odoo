/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { CopyButton } from "./copy_button";
import { UrlField } from "../url/url_field";
import { CharField } from "../char/char_field";
import { TextField } from "../text/text_field";
import { standardFieldProps } from "../standard_field_props";

const { Component } = owl;

class CopyClipboardField extends Component {
    setup() {
        this.copyText = this.env._t("Copy");
        this.successText = this.env._t("Copied");
    }
}
CopyClipboardField.template = "web.CopyClipboardField";
CopyClipboardField.props = {
    ...standardFieldProps,
};

export class CopyClipboardCharField extends CopyClipboardField {}

CopyClipboardCharField.components = { Field: CharField, CopyButton };
CopyClipboardCharField.displayName = _lt("Copy Text to Clipboard");
CopyClipboardCharField.supportedTypes = ["char"];

registry.category("fields").add("CopyClipboardChar", CopyClipboardCharField);

export class CopyClipboardTextField extends CopyClipboardField {}

CopyClipboardTextField.components = { Field: TextField, CopyButton };
CopyClipboardTextField.displayName = _lt("Copy Multiline Text to Clipboard");
CopyClipboardTextField.supportedTypes = ["text"];

registry.category("fields").add("CopyClipboardText", CopyClipboardTextField);

export class CopyClipboardURLField extends CopyClipboardField {}

CopyClipboardURLField.components = { Field: UrlField, CopyButton };
CopyClipboardURLField.displayName = _lt("Copy URL to Clipboard");
CopyClipboardURLField.supportedTypes = ["char"];

registry.category("fields").add("CopyClipboardURL", CopyClipboardURLField);
