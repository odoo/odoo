/** @odoo-module */

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

const { Component, onWillUpdateProps, useState } = owl;

const BLACK_LISTED_PATHS = [
    "/action/search_view",
    "/action/_originalAction",
];

class JSONFieldWidget extends Component {

    static template = "exception_tracker.JSONFieldWidget";
    static components = { JSONFieldWidget };

    setup() {
        this.value = JSON.parse(this.props.record.data[this.props.name]);
        onWillUpdateProps((nextProps) => {
            this.value = JSON.parse(nextProps.record.data[nextProps.name]);
        });
        this.state = useState({ opened: [] });
    }

    formatValue(value) {
        if (typeof value === "string" || value instanceof String) {
            return `"${value}"`;
        }
        if (value instanceof Array) {
            return `[...]`;
        }
        if (value instanceof Object) {
            return `{...}`;
        }
        if (value === null) { 
            return "null";
        }
        if (value === undefined) {
            return "undefined";
        }
        return value;
    }

    isInBlackList(path) {
        return BLACK_LISTED_PATHS.includes(path);
    }

    formatEmptyValue(value) {
        if (this.isArray(value)) {
            return "[]";
        }
        if (this.isDict(value)) {
            return "{}";
        }
        return "";
    }

    isToggableEmpty(value) {
        if (value instanceof Array) {
            return !Boolean(value.length);
        }
        if (value instanceof Object) {
            return Object.keys(value).length === 0 && value.constructor === Object;
        }
        return false;
    }

    maxKeyLength(obj) {
        return Object.keys(obj).reduce((acc, key) => {
            if (key.length > acc) {
                return key.length;
            }
            return acc;
        }, 0);
    }

    isDict(value) {
        if (value instanceof Object && !(value instanceof Array)) {
            return true;
        }
        return false;
    }

    isArray(value) {
        if (value instanceof Array) {
            return true;
        }
        return false;
    }

    addPath(path) {
        if (!this.state.opened.includes(path)) {
            this.state.opened.push(path);
        }
    }

    removePath(path) {
        this.state.opened = this.state.opened.filter(function (item) {
            return item !== path;
        });
    }

    isOpened(path) {
        return this.state.opened.includes(path);
    }

    getRecursiveProps(jsonString) {

        const normalize = (dataString) => {
            let newString = dataString;
            newString = newString.replaceAll(`'`, `"`);
            newString = newString.replaceAll(`"`, `\\\"`);
            newString = newString.replaceAll(`{\\\"`, `{"`);
            newString = newString.replaceAll(`\\\"}`, `"}`);
            newString = newString.replaceAll(`\\\"  : \\\"`, `" : "`);
            return newString;
          };
        const cleanedJsonString = normalize(jsonString);
        debugger;
        return { ...this.props, value: cleanedJsonString };
    }

    isTogglable(value) {
        if (value instanceof Array) {
            return true;
        }
        if (value instanceof Object) {
            return true;
        }
        return false;
    }
}

export const jsonFieldWidget = {
    component: JSONFieldWidget,
    displayName: _lt("Logs"),
};

registry.category("fields").add("json", jsonFieldWidget);
