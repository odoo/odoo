import { Component, useSubEnv, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { defaultBuilderComponents } from "../core/building_blocks/default_builder_components";
import {
    useVisibilityObserver,
    useApplyVisibility,
    useIsActiveItem,
} from "../core/building_blocks/utils";
import { DependencyManager } from "../core/plugins/dependency_manager";
import { getSnippetName } from "@html_builder/utils/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator";
import { ShadowOption } from "@html_builder/plugins/shadow_option";

export class OptionsContainer extends Component {
    static template = "html_builder.OptionsContainer";
    static components = { ...defaultBuilderComponents, BorderConfigurator, ShadowOption };
    static props = {
        snippetModel: { type: Object },
        options: { type: Array },
        editingElement: true, // HTMLElement from iframe
        isRemovable: false,
        canHaveAnchor: false,
    };

    setup() {
        this.notification = useService("notification");

        useSubEnv({
            dependencyManager: new DependencyManager(),
            getEditingElement: () => this.props.editingElement,
            getEditingElements: () => [this.props.editingElement],
            weContext: {},
        });
        this.isActiveItem = useIsActiveItem();
        useVisibilityObserver("content", useApplyVisibility("root"));
    }

    get title() {
        return getSnippetName(this.env.getEditingElement());
    }

    // Checks if the element can be saved as a custom snippet.
    get isSavable() {
        const selector = "[data-snippet], a.btn";
        // TODO `so_submit_button_selector` ?
        const exclude = ".o_no_save, .s_donation_donate_btn, .s_website_form_send";
        const el = this.props.editingElement;
        return el.matches(selector) && !el.matches(exclude);
    }

    selectElement() {
        this.env.editor.shared["builder-options"].updateContainers(this.props.editingElement);
    }

    toggleOverlayPreview(el, show) {
        if (show) {
            this.env.editor.shared.overlayButtons.hideOverlayButtons();
            this.env.editor.shared.builderOverlay.showOverlayPreview(el);
        } else {
            this.env.editor.shared.overlayButtons.showOverlayButtons();
            this.env.editor.shared.builderOverlay.hideOverlayPreview(el);
        }
    }

    onMouseEnter() {
        this.toggleOverlayPreview(this.props.editingElement, true);
    }

    onMouseLeave() {
        this.toggleOverlayPreview(this.props.editingElement, false);
    }

    // Actions of the buttons in the title bar.
    removeElement() {
        this.env.editor.shared.remove.removeElement(this.props.editingElement);
    }

    cloneElement() {
        this.env.editor.shared.clone.cloneElement(this.props.editingElement, {
            scrollToClone: true,
        });
    }

    async saveSnippet() {
        const savedName = await this.props.snippetModel.saveSnippet(
            this.props.editingElement,
            this.env.editor.resources["clean_for_save_handlers"]
        );
        if (savedName) {
            const message = markup(
                _t(
                    "Your custom snippet was successfully saved as <strong>%s</strong>. Find it in your snippets collection.",
                    savedName
                )
            );
            this.notification.add(message, {
                type: "success",
                autocloseDelay: 5000,
            });
        }
    }

    async createOrEditAnchorLink() {
        await this.env.editor.shared.anchor.createOrEditAnchorLink(this.props.editingElement);
    }
}
