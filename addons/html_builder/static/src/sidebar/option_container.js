import { getSnippetName, useOptionsSubEnv } from "@html_builder/utils/utils";
import { asyncComputed, onMounted, onWillStart, useProps, signal, t, useListener } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import { uniqueId } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";
import { BaseOptionComponent } from "../core/base_option_component";
import { useOperation } from "../core/operation_plugin";
import { _t } from "@web/core/l10n/translation";
import { useApplyVisibility, useGetItemValue, useVisibilityObserver } from "../core/utils";

const HIGHLIGHT_DURATION = 2000;

export class OptionsContainer extends BaseOptionComponent {
    static template = "html_builder.OptionsContainer";
    static dependencies = ["builderOptions", "remove", "clone"];
    props = useProps({
        toggleOverlayPreview: t.function().optional(() => () => {}),
        options: t.array(),
        editingElement: t.any(), // HTMLElement from iframe
        isRemovable: t.boolean().optional(false),
        toggleFold: t.function().optional(),
        folded: t.boolean().optional(),
        removeDisabledReason: t.string().optional(),
        isClonable: t.boolean().optional(false),
        cloneDisabledReason: t.string().optional(),
        optionTitleComponents: t.array().optional([]),
        containerTopButtons: t.array(),
        containerTitle: t.object().optional({}),
        headerMiddleButtons: t.array().optional([]),
        highlight: t.boolean().optional(false),
    });
    rootRef = signal.ref();
    contentRef = signal.ref();

    setup() {
        useOptionsSubEnv(() => [this.props.editingElement]);
        super.setup();
        this.containerId = uniqueId("option-container-");
        this.notification = useService("notification");
        this.getItemValue = useGetItemValue();
        useVisibilityObserver(this.contentRef, useApplyVisibility(this.rootRef));

        useListener(browser, "focusin", this.updateOverlayPreview.bind(this));
        useListener(browser, "pointermove", this.updateOverlayPreview.bind(this));
        useListener(this.document, "pointermove", this.updateOverlayPreview.bind(this));
        this.showingOverlayPreview = false;

        this.callOperation = useOperation();

        this.hasGroup = {};
        this.options = asyncComputed(() => this.filterAccessGroup(this.props.options), {
            initial: [],
        });
        onWillStart(() => this.options.currentPromise());
        onMounted(() => {
            const rootEl = this.rootRef();
            if (this.props.highlight && rootEl) {
                rootEl.scrollIntoView({ behavior: "smooth", block: "center" });
                rootEl.classList.add("o-options-container-highlight");
                // The highlight animation runs on sibling option containers, so
                // the highlight class is removed here instead of using an
                // "animation-end" event listener.
                setTimeout(
                    () => rootEl.classList.remove("o-options-container-highlight"),
                    HIGHLIGHT_DURATION
                );
            }
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
        for (const option of this.options()) {
            title = option.title || title;
        }
        const titleExtraInfo = this.props.containerTitle.getTitleExtraInfo
            ? this.props.containerTitle.getTitleExtraInfo(this.props.editingElement)
            : "";

        return (title || getSnippetName(this.env.getEditingElement())) + titleExtraInfo;
    }

    /** @param {PointerEvent | FocusEvent} ev */
    updateOverlayPreview(ev) {
        const shouldShow = this.rootRef()?.contains(ev.target);
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

    /**
     * Reads all stylistic DOM state (classes, inline styles, data attributes)
     * from the currently active editing element and stores it in the plugin.
     */
    copyStyles() {
        this.dependencies.builderOptions.copyStyles(this.props.editingElement);
        this.notification.add(_t("Styles copied"), { type: "success" });
    }

    /**
     * Applies the previously copied styles onto the current editing element,
     * provided the target element has at least one compatible option plugin.
     */
    pasteStyles() {
        const actionsToApply = this.dependencies.builderOptions.getStylesToPaste(
            this.props.editingElement
        );
        if (!actionsToApply || !actionsToApply.length) {
            return;
        }

        this.callOperation(async () => {
            const getAction = this.env.editor.shared.builderActions.getAction;
            for (const { actionId, actionParam, actionValue } of actionsToApply) {
                const action = getAction(actionId);
                if (action?.apply) {
                    await action.apply({
                        editingElement: this.props.editingElement,
                        params: actionParam,
                        value: actionValue,
                        dependencyManager: this.env.dependencyManager,
                        selectableContext: this.env.selectableContext,
                    });
                }
            }
        });
        this.notification.add(_t("Styles pasted"), { type: "success" });
    }
}
