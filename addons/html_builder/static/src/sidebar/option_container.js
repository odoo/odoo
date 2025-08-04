import { BorderConfigurator } from "../plugins/border_configurator_option";
import { ShadowOption } from "../plugins/shadow_option";
import { getSnippetName, useOptionsSubEnv } from "@html_builder/utils/utils";
import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { user } from "@web/core/user";
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
        removeDisabledReason: { type: String, optional: true },
        isClonable: false,
        cloneDisabledReason: { type: String, optional: true },
        optionTitleComponents: { type: Array, optional: true },
        containerTopButtons: { type: Array },
        containerTitle: { type: Object, optional: true },
        headerMiddleButtons: { type: Array, optional: true },
    };
    static defaultProps = {
        containerTitle: {},
        headerMiddleButtons: [],
        optionTitleComponents: [],
    };

    setup() {
        useOptionsSubEnv(() => [this.props.editingElement]);
        super.setup();
        this.notification = useService("notification");
        this.getItemValue = useGetItemValue();
        useVisibilityObserver("content", useApplyVisibility("root"));

        this.callOperation = useOperation();
        this.state = useState({
            isUpToDate: this.env.editor.shared.versionControl.hasAccessToOutdatedEl(
                this.props.editingElement
            ),
        });

        this.hasGroup = {};
        onWillStart(async () => {
            await this.updateAccessGroup(this.props.options);
        });
        onWillUpdateProps(async (nextProps) => {
            await this.updateAccessGroup(nextProps.options);
        });
    }

    async updateAccessGroup(options) {
        const proms = [];
        const groups = [...new Set(options.flatMap((o) => o.groups || []))];
        for (const group of groups) {
            proms.push(
                user.hasGroup(group).then((result) => {
                    this.hasGroup[group] = result;
                })
            );
        }
        await Promise.all(proms);
    }

    hasAccess(groups) {
        if (!groups) {
            return true;
        }
        return groups.every((group) => this.hasGroup[group]);
    }

    get title() {
        let title;
        for (const option of this.props.options) {
            title = option.title || title;
        }
        const titleExtraInfo = this.props.containerTitle.getTitleExtraInfo
            ? this.props.containerTitle.getTitleExtraInfo(this.props.editingElement)
            : "";

        return (title || getSnippetName(this.env.getEditingElement())) + titleExtraInfo;
    }

    selectElement() {
        this.env.editor.shared["builderOptions"].updateContainers(this.props.editingElement);
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

    onPointerEnter() {
        this.toggleOverlayPreview(this.props.editingElement, true);
    }

    onPointerLeave() {
        this.toggleOverlayPreview(this.props.editingElement, false);
    }

    // Actions of the buttons in the title bar.
    removeElement() {
        this.callOperation(() => {
            this.env.editor.shared.remove.removeElement(this.props.editingElement);
        });
    }

    cloneElement() {
        this.callOperation(async () => {
            await this.env.editor.shared.clone.cloneElement(this.props.editingElement, {
                activateClone: false,
            });
        });
    }

    // Version control
    replaceElementWithNewVersion() {
        this.callOperation(() => {
            this.env.editor.shared.versionControl.replaceWithNewVersion(this.props.editingElement);
        });
    }
    accessOutdated() {
        this.env.editor.shared.versionControl.giveAccessToOutdatedEl(this.props.editingElement);
        this.state.isUpToDate = true;
    }
}
