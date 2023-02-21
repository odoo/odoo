/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";
import { evalDomain } from "@web/views/utils";
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
        this.copyText = this.props.string || this.env._t("Copy");
        this.successText = this.env._t("Copied");
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
        const context = this.props.record.evalContext;
        const evaluated = this.props.disabledExpr ? evaluateExpr(this.props.disabledExpr) : false;
        if (evaluated instanceof Array) {
            return evalDomain(evaluated, context);
        }
        return Boolean(evaluated);
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
    displayName: _lt("Copy to Clipboard"),
    extractProps,
};

registry.category("fields").add("CopyClipboardButton", copyClipboardButtonField);

export const copyClipboardCharField = {
    component: CopyClipboardCharField,
    displayName: _lt("Copy Text to Clipboard"),
    supportedTypes: ["char"],
    extractProps,
};

registry.category("fields").add("CopyClipboardChar", copyClipboardCharField);

export const copyClipboardTextField = {
    component: CopyClipboardTextField,
    displayName: _lt("Copy Multiline Text to Clipboard"),
    supportedTypes: ["text"],
    extractProps,
};

registry.category("fields").add("CopyClipboardText", copyClipboardTextField);

export const copyClipboardURLField = {
    component: CopyClipboardURLField,
    displayName: _lt("Copy URL to Clipboard"),
    supportedTypes: ["char"],
    extractProps,
};

registry.category("fields").add("CopyClipboardURL", copyClipboardURLField);
