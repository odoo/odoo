/** @odoo-module **/

import { loadAssets } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { useEffect } from "@web/core/utils/hooks";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;
const { onWillStart, useRef } = owl.hooks;

export class AceField extends Component {
    setup() {
        this.aceEditor = null;
        this.editorRef = useRef("editor");

        onWillStart(async () => {
            await loadAssets({
                jsLibs: ["/web/static/lib/ace/ace.js"],
            });
            await loadAssets({
                jsLibs: [
                    "/web/static/lib/ace/mode-python.js",
                    "/web/static/lib/ace/mode-xml.js",
                    "/web/static/lib/ace/mode-qweb.js",
                ],
            });
        });

        useEffect(
            () => {
                this.setupAce();
                return () => this.destroyAce();
            },
            () => []
        );
        useEffect(() => {
            this.patchAce();
        });
    }

    get aceSession() {
        return this.aceEditor.getSession();
    }
    get mode() {
        return this.props.options.mode || "qweb";
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

        this.aceEditor.on("blur", this.onBlur.bind(this));
    }
    patchAce() {
        const formattedValue = this.props.formatValue(this.props.value) || "";
        if (this.aceSession.getValue() !== formattedValue) {
            this.aceSession.setValue(formattedValue);
        }

        this.aceSession.setOptions({
            mode: `ace/mode/${this.mode === "xml" ? "qweb" : this.mode}`,
        });

        this.aceEditor.setOptions({
            highlightActiveLine: !this.props.readonly,
            highlightGutterLine: !this.props.readonly,
            readOnly: this.props.readonly,
        });
        this.aceEditor.renderer.setOptions({
            displayIndentGuides: !this.props.readonly,
            showGutter: !this.props.readonly,
        });

        this.aceEditor.renderer.$cursorLayer.element.style.display = this.props.readonly
            ? "none"
            : "block";
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

Object.assign(AceField, {
    template: "web.AceField",
    props: {
        ...standardFieldProps,
    },

    supportedTypes: ["text"],
});

registry.category("fields").add("ace", AceField);
