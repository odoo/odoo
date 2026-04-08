import { useExternalListener, useRef } from "@web/owl2/utils";
import { getSnippetName, useOptionsSubEnv } from "@html_builder/utils/utils";
import { onWillStart, onWillUpdateProps } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useOperation } from "../core/operation_plugin";
import { BaseOptionComponent } from "../core/base_option_component";
import { useApplyVisibility, useGetItemValue, useVisibilityObserver } from "../core/utils";
import { uniqueId } from "@web/core/utils/functions";
import { browser } from "@web/core/browser/browser";

export class OptionsContainer extends BaseOptionComponent {
    static template = "html_builder.OptionsContainer";
    static dependencies = ["builderOptions", "remove", "clone"];
    static props = {
        toggleOverlayPreview: { type: Function, optional: true },
        options: { type: Array },
        editingElement: true, // HTMLElement from iframe
        isRemovable: { type: Boolean, optional: true },
        toggleFold: { type: Function, optional: true },
        folded: { type: Boolean, optional: true },
        removeDisabledReason: { type: String, optional: true },
        isClonable: { type: Boolean, optional: true },
        cloneDisabledReason: { type: String, optional: true },
        optionTitleComponents: { type: Array, optional: true },
        containerTopButtons: { type: Array },
        containerTitle: { type: Object, optional: true },
        headerMiddleButtons: { type: Array, optional: true },
    };
    static defaultProps = {
        toggleOverlayPreview: () => {},
        containerTitle: {},
        headerMiddleButtons: [],
        optionTitleComponents: [],
        isRemovable: false,
        isClonable: false,
    };

    setup() {
        useOptionsSubEnv(() => [this.props.editingElement]);
        super.setup();
        this.containerId = uniqueId("option-container-");
        this.notification = useService("notification");
        this.getItemValue = useGetItemValue();
        useVisibilityObserver("content", useApplyVisibility("root"));

        this.rootRef = useRef("root");
        useExternalListener(browser, "focusin", this.updateOverlayPreview);
        useExternalListener(browser, "pointermove", this.updateOverlayPreview);
        useExternalListener(this.document, "pointermove", this.updateOverlayPreview);
        this.showingOverlayPreview = false;

        this.callOperation = useOperation();

        this.options = [];
        this.hasGroup = {};
        onWillStart(async () => {
            this.options = await this.filterAccessGroup(this.props.options);
        });
        onWillUpdateProps(async (nextProps) => {
            this.options = await this.filterAccessGroup(nextProps.options);
        });
    }

    async filterAccessGroup(options) {
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
        return options.filter((option) => this.hasAccess(option.groups));
    }

    hasAccess(groups) {
        if (!groups) {
            return true;
        }
        return groups.every((group) => this.hasGroup[group]);
    }

    get title() {
        let title;
        for (const option of this.options) {
            title = option.title || title;
        }
        const titleExtraInfo = this.props.containerTitle.getTitleExtraInfo
            ? this.props.containerTitle.getTitleExtraInfo(this.props.editingElement)
            : "";

        return (title || getSnippetName(this.env.getEditingElement())) + titleExtraInfo;
    }

    /** @param {PointerEvent | FocusEvent} ev */
    updateOverlayPreview(ev) {
        const shouldShow = this.rootRef.el?.contains(ev.target);
        if (shouldShow === this.showingOverlayPreview) {
            return;
        }
        this.props.toggleOverlayPreview(this.props.editingElement, shouldShow);
        this.showingOverlayPreview = shouldShow;
    }

    // Actions of the buttons in the title bar.
    removeElement() {
        this.callOperation(() => {
            this.dependencies.remove.removeElement(this.props.editingElement);
        });
    }

    cloneElement() {
        this.callOperation(async () => {
            await this.dependencies.clone.cloneElement(this.props.editingElement, {
                activateClone: false,
            });
        });
    }
}
