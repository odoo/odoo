import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { defaultBuilderComponents } from "../core/default_builder_components";
import {
    useVisibilityObserver,
    useApplyVisibility,
    useIsActiveItem,
    useGetItemValue,
} from "../core/building_blocks/utils";
import { getSnippetName, useOptionsSubEnv } from "@html_builder/utils/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator";
import { ShadowOption } from "@html_builder/plugins/shadow_option";
import { useOperation } from "../core/plugins/operation_plugin";

export class OptionsContainer extends Component {
    static template = "html_builder.OptionsContainer";
    static components = {
        ...defaultBuilderComponents,
        BorderConfigurator,
        ShadowOption,
    };
    static props = {
        snippetModel: { type: Object },
        options: { type: Array },
        editingElement: true, // HTMLElement from iframe
        isRemovable: false,
        isClonable: false,
        containerTopButtons: { type: Array },
        headerMiddleButtons: { type: Array, optional: true },
    };
    static defaultProps = {
        headerMiddleButtons: [],
    };

    setup() {
        this.notification = useService("notification");
        useOptionsSubEnv(() => [this.props.editingElement]);
        this.isActiveItem = useIsActiveItem();
        this.getItemValue = useGetItemValue();
        useVisibilityObserver("content", useApplyVisibility("root"));

        this.callOperation = useOperation();
    }

    get title() {
        return getSnippetName(this.env.getEditingElement());
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
        this.callOperation(() => {
            this.env.editor.shared.remove.removeElement(this.props.editingElement);
        });
    }

    cloneElement() {
        this.callOperation(() => {
            this.env.editor.shared.clone.cloneElement(this.props.editingElement, {
                scrollToClone: true,
            });
        });
    }
}
