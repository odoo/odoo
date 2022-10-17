/** @odoo-module */

import { registry } from "@web/core/registry";

const { Component, onWillUpdateProps, useState } = owl;

const BLACK_LISTED_PATHS = [
    "/action/search_view",
    "/action/_originalAction",
];

class JSONFieldWidget extends Component {
    setup() {
        this.value = JSON.parse(this.props.value);
        onWillUpdateProps((nextProps) => {
            this.value = JSON.parse(this.props.value);
        });
        this.state = useState({ opened: [] });
        console.log(this.value);
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

    formatKey(key, obj) {
        return key;
        const maxLength = this.maxKeyLength(obj);
        return key.padEnd(maxLength, " ");
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
JSONFieldWidget.template = "exception_tracker.JSONFieldWidget";

registry.category("fields").add("json", JSONFieldWidget);
