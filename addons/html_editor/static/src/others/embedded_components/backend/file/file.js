/** @odoo-module native */
import {
    applyObjectPropertyDifference,
    getEmbeddedProps,
    StateChangeManager,
    useEmbeddedState,
} from "@html_editor/others/embedded_component_utils";
import { ReadonlyEmbeddedFileComponent } from "@html_editor/others/embedded_components/core/file/readonly_file";
import { useEffect, useRef, useState } from "@odoo/owl";

export class EmbeddedFileComponent extends ReadonlyEmbeddedFileComponent {
    static template = "html_editor.EmbeddedFile";

    setup() {
        super.setup();
        this.state = useEmbeddedState(this.props.host);
        this.fileModel.state = this.state;
        this.localState = useState({
            editFileName: false,
        });
        this.nameInput = useRef("nameInput");
        useEffect(
            () => {
                if (this.localState.editFileName) {
                    this.nameInput.el.focus();
                    this.nameInput.el.select();
                }
            },
            () => [this.localState.editFileName],
        );
    }

    onBlurNameInput(ev) {
        this.localState.editFileName = false;
        this.renameFile();
    }

    onFocusFileName(ev) {
        this.localState.editFileName = true;
    }

    onKeydownNameInput(ev) {
        if (ev.key !== "Enter") {
            return;
        } else {
            ev.preventDefault();
        }
        if (this.renameFile()) {
            this.localState.editFileName = false;
            this.env.editorShared?.setSelectionAfter(this.props.host);
        }
    }

    renameFile() {
        let newName = this.nameInput.el.value;
        if (!newName.length) {
            return false;
        }
        if (newName === this.fileModel.filename) {
            return true;
        }
        this.fileModel.filename = newName;
        if (this.fileModel.extension) {
            const pattern = new RegExp(`\\.${this.fileModel.extension}$`, "i");
            if (!newName.match(pattern)) {
                newName += `.${this.fileModel.extension}`;
            }
        }
        this.fileModel.name = newName;
        return true;
    }
}

export const fileEmbedding = {
    name: "file",
    Component: EmbeddedFileComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
    getStateChangeManager: (config) =>
        new StateChangeManager(
            Object.assign(config, {
                propertyUpdater: {
                    fileData: (state, previous, next) => {
                        applyObjectPropertyDifference(
                            state,
                            "fileData",
                            previous.fileData,
                            next.fileData,
                        );
                    },
                },
            }),
        ),
};
