/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";

import { CopyButton } from "./copy_button";
import { UrlField } from "../url/url_field";
import { CharField } from "../char/char_field";
import { TextField } from "../text/text_field";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

class CopyClipboardField extends Component {
    static template = "web.CopyClipboardField";
    static props = {
        ...standardFieldProps,
        string: { type: String, optional: true },
        disabledExpr: { type: String, optional: true },
    };

    setup() {
        this.copyText = this.props.string || _t("Copy");
        this.successText = _t("Copied");
    }

    get copyButtonClassName() {
        return `o_btn_${this.type}_copy btn-sm`;
    }
    get fieldProps() {
        return omit(this.props, "string", "disabledExpr");
    }
    get type() {
        return this.props.record.fields[this.props.name].type;
    }
    get disabled() {
        return this.props.disabledExpr
            ? evaluateBooleanExpr(
                  this.props.disabledExpr,
                  this.props.record.evalContextWithVirtualIds
              )
            : false;
    }
}

export class CopyClipboardButtonField extends CopyClipboardField {
    static template = "web.CopyClipboardButtonField";
    static components = { CopyButton };

    get copyButtonClassName() {
        return `o_btn_${this.type}_copy rounded-2`;
    }
}

export class CopyClipboardCharField extends CopyClipboardField {
    static components = { Field: CharField, CopyButton };
}

export class CopyClipboardTextField extends CopyClipboardField {
    static components = { Field: TextField, CopyButton };
}

export class CopyClipboardURLField extends CopyClipboardField {
    static components = { Field: UrlField, CopyButton };
}

// ----------------------------------------------------------------------------

function extractProps({ attrs }) {
    return {
        string: attrs.string,
        disabledExpr: attrs.disabled,
    };
}

export const copyClipboardButtonField = {
    component: CopyClipboardButtonField,
    displayName: _t("Copy to Clipboard"),
    extractProps,
};

registry.category("fields").add("CopyClipboardButton", copyClipboardButtonField);

export const copyClipboardCharField = {
    component: CopyClipboardCharField,
    displayName: _t("Copy Text to Clipboard"),
    supportedTypes: ["char"],
    extractProps,
};

registry.category("fields").add("CopyClipboardChar", copyClipboardCharField);

export const copyClipboardTextField = {
    component: CopyClipboardTextField,
    displayName: _t("Copy Multiline Text to Clipboard"),
    supportedTypes: ["text"],
    extractProps,
};

registry.category("fields").add("CopyClipboardText", copyClipboardTextField);

export const copyClipboardURLField = {
    component: CopyClipboardURLField,
    displayName: _t("Copy URL to Clipboard"),
    supportedTypes: ["char"],
    extractProps,
};

registry.category("fields").add("CopyClipboardURL", copyClipboardURLField);
