import { Component, xml, useRef, onWillUpdateProps, useEffect } from "@odoo/owl";

function createCopyPopup(event) {
    const div = document.createElement("div");
    div.className = "o-doc-copy position-fixed bg-default rounded";
    div.innerText = "Copied!";
    document.body.appendChild(div);

    const rect = div.getBoundingClientRect();
    div.style.left = event.clientX - rect.width / 2.0 + "px";
    div.style.top = event.clientY - rect.height + "px";

    div.animate(
        [
            { transform: "translateY(0px)", opacity: 1 },
            { transform: "translateY(-20px)", opacity: 0 },
        ],
        {
            duration: 1000,
        }
    );

    setTimeout(() => div.remove(), 990);
}

export class CodeViewer extends Component {
    static template = xml`
        <div class="o-doc-code-viewer position-relative p-2 rounded">
            <div class="w-100" t-ref="editorRef" t-att-data-mode="props.language"></div>
            <div class="o-doc-code-viewer-floating position-absolute flex align-items-center top-1">
                <i class="o-copy-btn cursor-pointer fa fa-clipboard" t-on-click="copyToClipboard">
                </i>
            </div>
        </div>
    `;
    static props = {
        value: { type: String },
        class: { type: String, optional: true },
        language: { type: String, optional: true },
        editable: { type: Boolean, optional: true },
        onChange: { type: Function, optional: true },
    };
    static defaultProps = {
        class: "",
    };

    setup() {
        this.editorRef = useRef("editorRef");

        useEffect(
            (el) => {
                if (!el) {
                    return;
                }

                const aceEditor = window.ace.edit(el);
                this.aceEditor = aceEditor;

                this.aceEditor.setOptions({
                    useWorker: false,
                    maxLines: Infinity,
                });

                this.aceEditor.renderer.setOptions({
                    fontSize: "1em",
                    showGutter: false,
                    showPrintMargin: false,
                    displayIndentGuides: true,
                    theme: "ace/theme/monokai",
                });

                const session = aceEditor.getSession();
                session.setValue(this.props.value);
                session.on("change", () => {
                    if (this.props.editable) {
                        this.props.onChange?.(this.aceEditor.getValue());
                    }
                });

                this.updateOptions(this.props);

                return () => {
                    aceEditor.destroy();
                };
            },
            () => [this.editorRef.el]
        );

        onWillUpdateProps((props) => this.updateOptions(props));
    }

    updateOptions(props) {
        const session = this.aceEditor.getSession();
        this.aceEditor.setOption("readOnly", !props.editable);
        session.setMode(`ace/mode/${props.language}`);
        if (session.getValue() !== props.value) {
            session.setValue(props.value);
        }
    }

    copyToClipboard(event) {
        navigator?.clipboard?.writeText(this.props.value);
        createCopyPopup(event);
    }
}
