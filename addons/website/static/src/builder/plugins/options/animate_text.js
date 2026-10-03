import { DependencyManager } from "@html_builder/core/dependency_manager";
import { Component, proxy, useListener, useProps, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useSubEnv } from "@web/owl2/utils";
import { AnimateOption, animateOptionProps } from "./animate_option";

/**
 * Animation as a section of the Effects panel. Opening it does not animate
 * anything: the text is animated when an animation is picked, and "None"
 * removes it.
 */
export class AnimateSection extends Component {
    static template = "website_builder.AnimateSection";
    static components = { AnimateOption, Dropdown, DropdownItem };
    props = useProps({
        config: t.object({ editor: t.object(), editorBus: t.object() }),
        animateOptionProps: t.object(animateOptionProps),
        getAnimatedTexts: t.function(),
        getAnimatedTextOrCreateDefault: t.function(),
        isDisabled: t.function(),
    });

    setup() {
        this.activeElements = this.props.getAnimatedTexts();
        this.state = proxy({ hasAnimation: this.activeElements.length > 0 });
        // Follow the page: "None" unwraps the animated text.
        useListener(this.props.config.editorBus, "DOM_UPDATED", () => {
            if (this.activeElements.some((el) => !el.isConnected)) {
                this.activeElements = this.props.getAnimatedTexts();
                this.state.hasAnimation = this.activeElements.length > 0;
            }
        });
        useSubEnv({
            dependencyManager: new DependencyManager(),
            getEditingElement: () => this.activeElements?.[0],
            getEditingElements: () => this.activeElements || [],
            weContext: {},
            editor: this.props.config.editor,
            editorBus: this.props.config.editorBus,
            services: this.props.config.editor.services,
        });
    }

    /**
     * @param {boolean} [onScroll] animate on scroll instead of on appearance
     */
    addAnimation(onScroll = false) {
        const { elements } = this.props.getAnimatedTextOrCreateDefault();
        if (!elements?.length) {
            return;
        }
        if (onScroll) {
            // Same classes and zone as the "On Scroll" item of the option.
            for (const el of elements) {
                el.classList.add("o_animate_on_scroll");
                el.dataset.scrollZoneStart = 0;
                el.dataset.scrollZoneEnd = 100;
            }
            this.props.config.editor.shared.history.commit();
        }
        this.activeElements = elements;
        this.state.hasAnimation = true;
    }
}
