import {
    getEditableDescendants,
    getEmbeddedProps,
    useEditableDescendants,
} from "@html_editor/others/embedded_component_utils";
import { Component, onMounted, onPatched, proxy, useListener } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

const sessionStorage = browser.sessionStorage;
export class EmbeddedToggleBlockComponent extends Component {
    static template = "html_editor.EmbeddedToggleBlock";
    static props = {
        host: { type: Object },
        toggleBlockId: { type: String },
    };

    setup() {
        useEditableDescendants(this.props.host);
        this.state = proxy({
            showContent: sessionStorage.getItem(this.toggleStorageKey) === "true",
        });
        this.neutralRestoreSelection = () => {};
        this.restoreSelection = this.neutralRestoreSelection;
        useListener(this.props.host, "forceToggle", this.onToggle.bind(this));
        const restoreSelection = () => {
            this.restoreSelection();
            this.restoreSelection = this.neutralRestoreSelection;
        };
        onMounted(restoreSelection);
        onPatched(restoreSelection);
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
