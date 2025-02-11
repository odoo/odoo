import {
    getEditableDescendants,
    getEmbeddedProps,
    useEditableDescendants,
} from "@html_editor/others/embedded_component_utils";
import { browser } from "@web/core/browser/browser";
import { Component, useEffect, useExternalListener, useState } from "@odoo/owl";

const sessionStorage = browser.sessionStorage;
export class EmbeddedToggleBlockComponent extends Component {
    static template = "html_editor.EmbeddedToggleBlock";
    static props = {
        host: { type: Object },
        toggleBlockId: { type: String },
    };

    setup() {
        useEditableDescendants(this.props.host);
        this.state = useState({
            showContent: sessionStorage.getItem(this.toggleStorageKey) === "true",
        });
        this.neutralRestoreSelection = () => {};
        this.restoreSelection = this.neutralRestoreSelection;
        useExternalListener(this.props.host, "forceToggle", this.onToggle);
        useEffect(
            () => {
                this.restoreSelection();
                this.restoreSelection = this.neutralRestoreSelection;
            },
            () => [this.restoreSelection]
        );
    }

    get toggleStorageKey() {
        return `html_editor.ToggleBlock${this.props.toggleBlockId}.showContent`;
    }

    onToggle(ev) {
        let { showContent, restoreSelection } = ev.detail ?? {};
        showContent ??= !this.state.showContent;
        restoreSelection ??= this.neutralRestoreSelection;
        if (this.state.showContent !== showContent) {
            this.restoreSelection = restoreSelection;
            this.state.showContent = showContent;
            sessionStorage.setItem(this.toggleStorageKey, this.state.showContent);
        } else {
            restoreSelection();
        }
    }
}

export const toggleBlockEmbedding = {
    name: "toggleBlock",
    Component: EmbeddedToggleBlockComponent,
    getProps: (host) => ({ host, ...getEmbeddedProps(host) }),
    getEditableDescendants: getEditableDescendants,
};
