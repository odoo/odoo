/** @odoo-module **/
/* global ace */

import { loadJS } from "@web/core/assets";
import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { formatText } from "../formatters";
import { standardFieldProps } from "../standard_field_props";

import { Component, onWillStart, onWillUpdateProps, useEffect, useRef } from "@odoo/owl";

export class AceField extends Component {
    setup() {
        this.aceEditor = null;
        this.editorRef = useRef("editor");
        this.cookies = useService("cookie");

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

        onWillUpdateProps(this.updateAce);

        useEffect(
            () => {
                this.setupAce();
                this.updateAce(this.props);
                return () => this.destroyAce();
            },
            () => [this.editorRef.el]
        );

        useBus(this.env.bus, "RELATIONAL_MODEL:WILL_SAVE_URGENTLY", () => this.commitChanges());
        useBus(this.env.bus, "RELATIONAL_MODEL:NEED_LOCAL_CHANGES", ({ detail }) =>
            detail.proms.push(this.commitChanges())
        );
    }

    get aceSession() {
        return this.aceEditor.getSession();
    }

    setupAce() {
        this.aceEditor = ace.edit(this.editorRef.el);
        this.aceEditor.setOptions({
            maxLines: Infinity,
            showPrintMargin: false,
            theme: this.cookies.current.color_scheme === "dark" ? "ace/theme/monokai" : "",
        });
        this.aceEditor.$blockScrolling = true;

        this.aceSession.setOptions({
            useWorker: false,
            tabSize: 2,
            useSoftTabs: true,
        });

        this.aceEditor.on("blur", this.commitChanges.bind(this));
    }

    updateAce({ mode, readonly, value }) {
        if (!this.aceEditor) {
            return;
        }

        this.aceSession.setOptions({
            mode: `ace/mode/${mode === "xml" ? "qweb" : mode}`,
        });

        this.aceEditor.setOptions({
            readOnly: readonly,
            highlightActiveLine: !readonly,
            highlightGutterLine: !readonly,
        });

        this.aceEditor.renderer.setOptions({
            displayIndentGuides: !readonly,
            showGutter: !readonly,
        });

        this.aceEditor.renderer.$cursorLayer.element.style.display = readonly ? "none" : "block";

        const formattedValue = formatText(value);
        if (this.aceSession.getValue() !== formattedValue) {
            this.aceSession.setValue(formattedValue);
        }
    }

    destroyAce() {
        if (this.aceEditor) {
            this.aceEditor.destroy();
        }
    }

    commitChanges() {
        if (!this.props.readonly) {
            const value = this.aceSession.getValue();
            if (this.props.value !== value) {
                return this.props.update(value);
            }
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

AceField.extractProps = ({ attrs }) => {
    return {
        mode: attrs.options.mode,
    };
};

registry.category("fields").add("ace", AceField);
