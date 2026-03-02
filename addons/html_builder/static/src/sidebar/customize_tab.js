import { useState } from "@web/owl2/utils";
import { Component, onWillUpdateProps } from "@odoo/owl";
import { OptionsContainer } from "./option_container";
import { useVisibilityObserver } from "../core/utils";
import { CustomizeComponent } from "@html_builder/sidebar/customize_component";

export class CustomizeTab extends Component {
    static template = "html_builder.CustomizeTab";
    static components = { CustomizeComponent, OptionsContainer };
    static props = {
        currentOptionsContainers: { type: Array, optional: true },
    };
    static defaultProps = {
        currentOptionsContainers: [],
    };

    setup() {
        this.state = useState({
            hasContent: true,
        });
        this.customizeComponent = useState(
            this.env.editor.shared.customizeTab.getCustomizeComponent()
        );
        useVisibilityObserver("content", (hasContent) => {
            this.state.hasContent = hasContent;
        });
        onWillUpdateProps((nextProps) => {
            if (
                !this.state.hasContent &&
                nextProps.currentOptionsContainers.length > 0 &&
                nextProps.currentOptionsContainers !== this.props.currentOptionsContainers
            ) {
                // Force a reconsideration of `content`
                this.state.hasContent = true;
            }
        });
        this.overlayPreviewedEl = null;
    }

    toggleOverlayPreview(el, show) {
        if (show && this.overlayPreviewedEl !== el) {
            if (this.overlayPreviewedEl) {
                this.env.editor.shared.builderOverlay.hideOverlayPreview(this.overlayPreviewedEl);
            }
            this.env.editor.shared.overlayButtons.hideOverlayButtons();
            this.env.editor.shared.builderOverlay.showOverlayPreview(el);
            this.overlayPreviewedEl = el;
        } else if (!show && this.overlayPreviewedEl === el) {
            this.env.editor.shared.overlayButtons.showOverlayButtons();
            this.env.editor.shared.builderOverlay.hideOverlayPreview(el);
            this.overlayPreviewedEl = null;
        }
    }

    getCurrentOptionsContainers() {
        const currentOptionsContainers = this.props.currentOptionsContainers;
        if (!currentOptionsContainers.length) {
            return this.env.editor.shared.builderOptions.getPageContainers();
        }
        return currentOptionsContainers;
    }
}
