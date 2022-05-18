/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

import { CopyButton } from "@web/core/copy_button/copy_button";
import { _lt } from "@web/core/l10n/translation";
import { UrlField } from "./url_field";
import { CharField } from "./char_field";
import { TextField } from "./text_field";

const { Component } = owl;

export class CopyClipboardCharField extends Component {}

CopyClipboardCharField.components = { Field: CharField, CopyButton };
CopyClipboardCharField.props = {
    ...standardFieldProps,
};
CopyClipboardCharField.template = "web.CopyClipboardField";
CopyClipboardCharField.displayName = _lt("Copy Text to Clipboard");
CopyClipboardCharField.supportedTypes = ["char"];

registry.category("fields").add("CopyClipboardChar", CopyClipboardCharField);

export class CopyClipboardTextField extends Component {}

CopyClipboardTextField.components = { Field: TextField, CopyButton };
CopyClipboardTextField.props = {
    ...standardFieldProps,
};
CopyClipboardTextField.template = "web.CopyClipboardField";
CopyClipboardTextField.displayName = _lt("Copy Multiline Text to Clipboard");
CopyClipboardTextField.supportedTypes = ["text"];

registry.category("fields").add("CopyClipboardText", CopyClipboardTextField);

export class CopyClipboardURLField extends Component {}

CopyClipboardURLField.components = { Field: UrlField, CopyButton };
CopyClipboardURLField.props = {
    ...standardFieldProps,
};
CopyClipboardURLField.template = "web.CopyClipboardField";
CopyClipboardURLField.displayName = _lt("Copy URL to Clipboard");
CopyClipboardURLField.supportedTypes = ["char"];

registry.category("fields").add("CopyClipboardURL", CopyClipboardURLField);
