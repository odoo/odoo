// @ts-check

/** @module @web/fields/basic/copy_clipboard/copy_clipboard_field - Wrapper field that adds a copy-to-clipboard button to Char/URL fields */

import { Component } from "@odoo/owl";
import { CopyButton } from "@web/components/copy_button/copy_button";
import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/collections/objects";
import { CharField } from "@web/fields/basic/char/char_field";
import { UrlField } from "@web/fields/basic/url/url_field";
import { standardFieldProps } from "@web/fields/standard_field_props";

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

    /** @returns {string} CSS class for the copy button */
    get copyButtonClassName() {
        return `o_btn_${this.type}_copy btn-sm`;
    }
    /** @returns {Object} Props forwarded to the inner field component */
    get fieldProps() {
        return omit(this.props, "string", "disabledExpr");
    }
    /** @returns {string} ORM field type */
    get type() {
        return this.props.record.fields[this.props.name].type;
    }
    /** @returns {boolean} Whether the copy button is disabled (from expression evaluation) */
    get disabled() {
        return this.props.disabledExpr
            ? evaluateBooleanExpr(
                  this.props.disabledExpr,
                  this.props.record.evalContextWithVirtualIds,
              )
            : false;
    }
}

/** Copy-to-clipboard variant rendered as a standalone button. */
export class CopyClipboardButtonField extends CopyClipboardField {
    static template = "web.CopyClipboardButtonField";
    static components = { CopyButton };
    static props = {
        ...CopyClipboardField.props,
        btnClass: { type: String, optional: true },
    };
    static defaultProps = {
        ...CopyClipboardField.defaultProps,
        btnClass: "primary",
    };

    get copyButtonClassName() {
        return `o_btn_${this.type}_copy btn-${this.props.btnClass} rounded-2`;
    }
}

export class CopyClipboardCharField extends CopyClipboardField {
    static components = { Field: CharField, CopyButton };

    /** @returns {string} Font Awesome icon class */
    get copyButtonIcon() {
        return "fa-clipboard";
    }
}

export class CopyClipboardURLField extends CopyClipboardField {
    static components = { Field: UrlField, CopyButton };

    /** @returns {string} Font Awesome icon class */
    get copyButtonIcon() {
        return "fa-link";
    }
}

// ----------------------------------------------------------------------------

/**
 * @param {{ string?: string, attrs: Record<string, string> }} fieldInfo
 * @returns {{ string?: string, disabledExpr?: string }}
 */
function extractProps({ string, attrs }) {
    return {
        string,
        disabledExpr: attrs.disabled,
    };
}

export const copyClipboardButtonField = {
    component: CopyClipboardButtonField,
    displayName: _t("Copy to Clipboard"),
    extractProps: (fieldInfo) => ({
        ...extractProps(fieldInfo),
        btnClass: fieldInfo.options.btn_class,
    }),
};

registry.category("fields").add("CopyClipboardButton", copyClipboardButtonField);

export const copyClipboardCharField = {
    component: CopyClipboardCharField,
    displayName: _t("Copy Text to Clipboard"),
    supportedTypes: ["char"],
    extractProps,
};

registry.category("fields").add("CopyClipboardChar", copyClipboardCharField);

export const copyClipboardURLField = {
    component: CopyClipboardURLField,
    displayName: _t("Copy URL to Clipboard"),
    supportedTypes: ["char"],
    extractProps,
};

registry.category("fields").add("CopyClipboardURL", copyClipboardURLField);
