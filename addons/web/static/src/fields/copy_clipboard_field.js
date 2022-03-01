/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

import { CopyButton } from "@web/core/copy_button/copy_button";
import { UrlField } from "./url_field";
import { CharField } from "./char_field";
import { TextField } from "./text_field";

const { Component } = owl;

export class CopyClipboardCharField extends Component {}

CopyClipboardCharField.TYPE = CharField;
CopyClipboardCharField.components = { CopyButton };
CopyClipboardCharField.props = {
    ...standardFieldProps,
};
CopyClipboardCharField.template = "web.CopyClipboardField";

registry.category("fields").add("CopyClipboardChar", CopyClipboardCharField);

export class CopyClipboardTextField extends Component {}

CopyClipboardTextField.TYPE = TextField;
CopyClipboardTextField.components = { CopyButton };
CopyClipboardTextField.props = {
    ...standardFieldProps,
};
CopyClipboardTextField.template = "web.CopyClipboardField";

registry.category("fields").add("CopyClipboardText", CopyClipboardTextField);

export class CopyClipboardURLField extends Component {}

CopyClipboardURLField.TYPE = UrlField;
CopyClipboardURLField.components = { CopyButton };
CopyClipboardURLField.props = {
    ...standardFieldProps,
};
CopyClipboardURLField.template = "web.CopyClipboardField";

registry.category("fields").add("CopyClipboardURL", CopyClipboardURLField);
