import { useOptionsSubEnv } from "@html_builder/utils/utils";
import { computed, onMounted, signal, t, useListener, useProps } from "@odoo/owl";
import { user } from "@web/core/user";
import { unique } from "@web/core/utils/arrays";
import { uniqueId } from "@web/core/utils/functions";
import { useAsyncComputed, useService } from "@web/core/utils/hooks";
import { BaseOptionComponent } from "../core/base_option_component";
import { useOperation } from "../core/operation_plugin";
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

    allGroups = computed(
        () => unique(this.props.options.flatMap(({ groups }) => groups || []).sort()),
        { equals: (a, b) => a.join() === b.join() }
    );
    hasGroup = useAsyncComputed(
        async () =>
            Object.fromEntries(
                await Promise.all(
                    this.allGroups().map(async (group) => [group, await user.hasGroup(group)])
                )
            ),
        { initial: {} }
    );
    options = computed(() => {
        const { options } = this.props;
        return options.filter(
            ({ groups }) => !groups || groups.every((group) => this.hasGroup()[group])
        );
    });

    setup() {
        useOptionsSubEnv(() => [this.props.editingElement]);
        super.setup();
        this.containerId = uniqueId("option-container-");
        this.notification = useService("notification");
        this.getItemValue = useGetItemValue();
        useVisibilityObserver(this.contentRef, useApplyVisibility(this.rootRef));

        useListener(window, "focusin", this.updateOverlayPreview.bind(this));
        useListener(window, "pointermove", this.updateOverlayPreview.bind(this));
        useListener(this.document, "pointermove", this.updateOverlayPreview.bind(this));
        this.showingOverlayPreview = false;

        this.callOperation = useOperation();

        onMounted(() => {
            const rootEl = this.rootRef();
            if (this.props.highlight && rootEl) {
                rootEl.scrollIntoView({ behavior: "smooth", block: "center" });
                rootEl.classList.add("o_hb_options_container_highlight");
                // The highlight animation runs on sibling option containers, so
                // the highlight class is removed here instead of using an
                // "animation-end" event listener.
                setTimeout(
                    () => rootEl.classList.remove("o_hb_options_container_highlight"),
                    HIGHLIGHT_DURATION
                );
            }
        });
    }

    get title() {
        let title;
        for (const option of this.options()) {
            title = option.title || title;
        }
        const titleExtraInfo = this.props.containerTitle.getTitleExtraInfo
            ? this.props.containerTitle.getTitleExtraInfo(this.props.editingElement)
            : "";

        return (
            (title ||
                this.env.editor.config.snippetModel.getSnippetName(this.env.getEditingElement())) +
            titleExtraInfo
        );
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
}
