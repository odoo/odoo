/** @odoo-module **/
/* global ace */

import { loadJS } from "@web/core/assets";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatText } from "../formatters";
import { standardFieldProps } from "../standard_field_props";

const { Component, onWillStart, useEffect, useRef } = owl;

export class AceField extends Component {
    setup() {
        this.aceEditor = null;
        this.editorRef = useRef("editor");

        onWillStart(async () => {
            await loadJS("/web/static/lib/ace/ace.js");
            const jsLibs = [
                "/web/static/lib/ace/mode-python.js",
                "/web/static/lib/ace/mode-xml.js",
                "/web/static/lib/ace/mode-qweb.js",
            ];
            const proms = jsLibs.map((url) => loadJS(url));
            return Promise.all(proms);
        });

        useEffect(() => {
            this.setupAce();
            return () => this.destroyAce();
        });
    }

    get aceSession() {
        return this.aceEditor.getSession();
    }

    setupAce() {
        this.aceEditor = ace.edit(this.editorRef.el);
        this.aceEditor.setOptions({
            maxLines: Infinity,
            showPrintMargin: false,
        });
        this.aceEditor.$blockScrolling = true;

        this.aceSession.setOptions({
            useWorker: false,
            tabSize: 2,
            useSoftTabs: true,
        });

        this.aceSession.setOptions({
            mode: `ace/mode/${this.props.mode === "xml" ? "qweb" : this.props.mode}`,
        });

        this.aceEditor.setOptions({
            readOnly: this.props.readonly,
            highlightActiveLine: !this.props.readonly,
            highlightGutterLine: !this.props.readonly,
        });

        this.aceEditor.renderer.setOptions({
            displayIndentGuides: !this.props.readonly,
            showGutter: !this.props.readonly,
        });

        this.aceEditor.renderer.$cursorLayer.element.style.display = this.props.readonly
            ? "none"
            : "block";

        const formattedValue = formatText(this.props.value);
        if (this.aceSession.getValue() !== formattedValue) {
            this.aceSession.setValue(formattedValue);
        }

        this.aceEditor.on("blur", this.onBlur.bind(this));
    }

    destroyAce() {
        if (this.aceEditor) {
            this.aceEditor.destroy();
        }
    }

    onBlur() {
        if (!this.props.readonly) {
            this.props.update(this.aceSession.getValue());
        }
    }
}

AceField.template = "web.AceField";
AceField.props = {
    ...standardFieldProps,
    mode: { type: String, optional: true },
};
AceField.defaultProps = {
    mode: "qweb",
};

AceField.displayName = _lt("Ace Editor");
AceField.supportedTypes = ["text"];

AceField.extractProps = (fieldName, record, attrs) => {
    return {
        mode: attrs.options.mode,
    };
};

registry.category("fields").add("ace", AceField);
