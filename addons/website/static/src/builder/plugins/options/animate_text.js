import { Component, onMounted, onWillDestroy, useChildSubEnv, useRef, useState } from "@odoo/owl";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { AnimateOption } from "./animate_option";
import { usePopover } from "@web/core/popover/popover_hook";
import { DependencyManager } from "@html_builder/core/dependency_manager";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { POSITION_BUS } from "@web/core/position/position_hook";

class AnimateTextPopover extends BaseOptionComponent {
    static template = "website_builder.AnimateTextPopover";
    static props = {
        animateOptionProps: AnimateOption.props,
        onReset: Function,

        // Popover service
        close: { type: Function, optional: true },
    };
    static components = { AnimateOption };

    setup() {
        super.setup();
        this.contentRef = useRef("content");
        this.resizeObserver = new ResizeObserver(() => {
            this.env[POSITION_BUS]?.trigger("update");
        });
        onMounted(() => {
            this.resizeObserver.observe(this.contentRef.el);
        });
        onWillDestroy(() => {
            this.resizeObserver.disconnect();
        });
    }
}

export class AnimateText extends Component {
    static template = "website_builder.AnimateText";
    static props = {
        ...toolbarButtonProps,
        config: { type: Object, shape: { editor: Object, editorBus: Object } },
        animateOptionProps: AnimateOption.props,
        getAnimatedTextOrCreateDefault: Function,
        isActive: Function,
        isDisabled: Function,
    };

    setup() {
        this.state = useState({});
        this.updateState();

        this.root = useRef("root");
        useChildSubEnv({
            dependencyManager: new DependencyManager(),
            getEditingElement: () => this.activeElement,
            getEditingElements: () => (this.activeElement ? [this.activeElement] : []),
            weContext: {},
            editor: this.props.config.editor,
            editorBus: this.props.config.editorBus,
            services: this.props.config.editor.services,
        });
        this.popover = usePopover(AnimateTextPopover, {
            env: this.__owl__.childEnv,
            onClose: () => {
                if (!this.props.config.editor.isDestroyed) {
                    this.updateState();
                }
            },
        });
    }

    onClick() {
        if (this.popover.isOpen) {
            return;
        }
        const { element, onReset } = this.props.getAnimatedTextOrCreateDefault();
        if (!element) {
            return;
        }
        this.activeElement = element;

        this.updateState();
        this.popover.open(this.root.el, {
            animateOptionProps: this.props.animateOptionProps,
            onReset: () => {
                onReset(this.activeElement);
                this.popover.close();
            },
        });
    }

    updateState() {
        this.state.isActive = this.props.isActive();
        this.state.isDisabled = this.props.isDisabled();
    }
}
