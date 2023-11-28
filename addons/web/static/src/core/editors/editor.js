/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { doFormatValue } from "@web/core/tree_editor/condition_tree";
import { omit, pick } from "@web/core/utils/objects";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef {Object} EditorInfo
 * @property {Function} isSupported
 * @property {Component} component
 * @property {Object} props
 * @property {Function} [serialize]
 * @property {Function} [message]
 */

function getFilteredProps(props, component) {
    if (component && component.props) {
        const keys = Array.isArray(component.props)
            ? component.props
            : Object.keys(component.props);
        if (keys.every((k) => k !== "*")) {
            return pick(props, ...keys);
        }
    }
    return props;
}

/**
 * @param {string} type
 * @param {Record<string,any>} [props={}]
 * @returns {EditorInfo}
 */
export function getEditorInfo(type, props = {}) {
    const factory = registry.category("editors").get(type);
    const info = factory(props);
    info.message ||= () => _t("Value not supported");
    info.serialize ||= doFormatValue;
    info.props = getFilteredProps({ ...props, ...info.props }, info.component);
    return info;
}

export class Editor extends Component {
    static template = "web.Editor";
    static props = {
        type: String,
        update: Function,
        value: { optional: true },
        className: { type: String, optional: true },
        "*": true,
    };

    setup() {
        onWillStart(() => this.computeDerivedParams(this.props));
        onWillUpdateProps((nextProps) => this.computeDerivedParams(nextProps));
    }

    computeDerivedParams(props) {
        const { type, value } = props;

        this.className = [`o_editor`, `o_editor_${type}`]
            .concat((props.className || "").split(" "))
            .join(" ");

        const genericProps = omit(props, "className"); // we never transfer className

        this.info = getEditorInfo(type, genericProps);

        this.valueIsSupported = this.info.isSupported(value);
        if (!this.valueIsSupported) {
            this.serializedValue = doFormatValue(value);
            this.message = this.info.message(value);
        }
    }

    onClear() {
        this.props.update(this.info.defaultValue());
    }
}
