import { Component, proxy, signal, t, useListener, useProps } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { useDropdownAutoVisibility } from "@html_editor/toolbar_dropdown_hook";

/**
 * Panel of the text effects: one collapsible section per effect, one open at a
 * time. A closed section shows the effect of the selection; each section
 * removes its effect with a "None" choice.
 */
export class EffectsPanel extends Component {
    static template = "html_builder.EffectsPanel";
    props = useProps({
        config: t.object({ editor: t.object(), editorBus: t.object() }).optional(),
        getSections: t.function(),
        close: t.function().optional(),
    });

    setup() {
        const sections = this.props.getSections();
        const openSection =
            sections.find((section) => section.isActive()) ||
            sections.find((section) => !section.isDisabled?.()) ||
            sections[0];
        this.state = proxy({
            openId: openSection?.id,
            // Bumped when the page changes, so that the summaries follow it.
            revision: 0,
        });
        if (this.props.config) {
            useListener(this.props.config.editorBus, "DOM_UPDATED", () => this.state.revision++);
        }
    }

    get sections() {
        return this.props.getSections();
    }

    toggle(section) {
        this.state.openId = this.state.openId === section.id ? undefined : section.id;
    }
}

export class EffectsButton extends Component {
    static template = "html_builder.EffectsButton";
    props = useProps({
        // from toolbarButtonProps
        title: t.or([t.string(), t.function()]),
        getSelection: t.function(),
        isDisabled: t.boolean(),
        config: t.object({ editor: t.object(), editorBus: t.object() }).optional(),
        getSections: t.function(),
    });

    buttonRef = signal.ref();

    setup() {
        this.state = proxy({ isOpen: false });
        const popoverRef = signal.ref();
        this.popover = usePopover(EffectsPanel, {
            ref: popoverRef,
            withScope: true,
            popoverClass: "o-we-effects-popover",
            onClose: () => {
                this.state.isOpen = false;
            },
        });
        useDropdownAutoVisibility(this.env.overlayState, popoverRef);
    }

    get isActive() {
        return this.state.isOpen || this.props.getSections().some((section) => section.isActive());
    }

    onClick() {
        if (this.popover.isOpen) {
            this.popover.close();
            return;
        }
        for (const section of this.props.getSections()) {
            section.prepare?.();
        }
        this.popover.open(this.buttonRef(), {
            config: this.props.config,
            getSections: this.props.getSections,
        });
        this.state.isOpen = true;
    }
}
