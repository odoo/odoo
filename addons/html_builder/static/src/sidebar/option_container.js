import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { ShadowOption } from "@html_builder/plugins/shadow_option";
import { getSnippetName, useOptionsSubEnv } from "@html_builder/utils/utils";
import { useService } from "@web/core/utils/hooks";
import { useOperation } from "../core/operation_plugin";
import {
    BaseOptionComponent,
    useApplyVisibility,
    useGetItemValue,
    useVisibilityObserver,
} from "../core/utils";

export class OptionsContainer extends BaseOptionComponent {
    static template = "html_builder.OptionsContainer";
    static components = {
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
        useOptionsSubEnv(() => [this.props.editingElement]);
        super.setup();
        this.notification = useService("notification");
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
