import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { effect } from "@web/core/utils/reactive";

export class LinkToolsPlugin extends Plugin {
    static name = "link_tools";
    static dependencies = ["link", "toolbar", "selection"];
    static shared = ["openLinkTools", "getLinktoolState"];
    /** @type { (p: LinkToolsPlugin) => Record<string, any> } */
    static resources = (p) => {
        p.buttonState = reactive({
            isActive: false,
        });
        return {
            mutation_filtered_classes: ["oe_edited_link"],
            onSelectionChange: p.onSelectionChange.bind(p),
            toolbarCategory: {
                id: "link",
                sequence: 40,
            },
            toolbarItems: [
                {
                    id: "link",
                    category: "link",
                    action() {
                        p.toggleLinkTools();
                    },
                    icon: "fa-link",
                    name: _t("link-tool"),
                    state: p.buttonState,
                },
            ],
        };
    };

    setup() {
        this.state = reactive({
            linkToolProps: undefined,
        });
        effect(
            (state) => {
                this.buttonState.isActive = Boolean(state.linkToolProps);
            },
            [this.state]
        );
    }
    getLinktoolState() {
        return this.state;
    }
    toggleLinkTools({ shouldFocusUrl = true } = {}) {
        if (!this.state.linkToolProps) {
            this.openLinkTools({ shouldFocusUrl });
        } else {
            this.closeLinkTools();
        }
    }
    /**
     * @param {Object} [options]
     * @param {boolean} [options.shouldFocusUrl] If true, the url input will be
     * focused.
     */
    openLinkTools({ shouldFocusUrl } = {}) {
        const link = this.shared.getOrCreateLink();
        this.currentLink = link;
        const self = this;

        this.state.linkToolProps = {
            ...this.config.linkOptions,
            wysiwyg: {
                odooEditor: {
                    observerUnactive() {},
                    observerActive() {},
                    get document() {
                        return self.document;
                    },
                    toggleLinkTools() {
                        console.warn("toggleLinkTools");
                    },
                    removeLink() {
                        console.warn("removeLink");
                    },

                    historyStep() {
                        self.dispatch("ADD_STEP");
                    },
                    execCommand() {
                        console.warn("execCommand");
                    },
                    historyPauseSteps() {
                        console.warn("historyPauseSteps");
                    },
                    historyUnpauseSteps() {
                        console.warn("historyUnpauseSteps");
                    },
                },
            },
            editable: this.editable,
            link,
            // If the link contains an image or an icon do not
            // display the label input (e.g. some mega menu links).
            needLabel: !link.querySelector(".fa, img"),
            shouldFocusUrl,
            getColorpickerTemplate: this.config.getColorpickerTemplatem,
        };
    }
    closeLinkTools() {
        this.state.linkToolProps = undefined;
    }
    onSelectionChange(selection) {
        if (!this.state.linkToolProps) {
            return;
        }
        const isInAnchor =
            selection.anchorNode === this.currentLink ||
            this.currentLink.contains(selection.anchorNode);
        const isInFocus =
            selection.focusNode === this.currentLink ||
            this.currentLink.contains(selection.focusNode);

        if (!isInAnchor || !isInFocus) {
            this.closeLinkTools();
        }
    }
}
