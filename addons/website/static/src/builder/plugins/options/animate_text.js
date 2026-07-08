import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { DependencyManager } from "@html_builder/core/dependency_manager";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { Component, onMounted, onWillDestroy, proxy, signal } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { POSITION_BUS } from "@web/core/position/position_hook";
import { useChildSubEnv } from "@web/owl2/utils";
import { AnimateOption } from "./animate_option";

export class AnimateTextPopover extends BaseOptionComponent {
    static template = "website_builder.AnimateTextPopover";
    static props = {
        animateOptionProps: AnimateOption.props,
        onReset: Function,

        // Popover service
        close: { type: Function, optional: true },
    };
    static components = { AnimateOption };
    contentRef = signal(null);

    setup() {
        super.setup();
        this.resizeObserver = new ResizeObserver(() => {
            this.env[POSITION_BUS]?.trigger("update");
        });
        onMounted(() => {
            this.resizeObserver.observe(this.contentRef());
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

    root = signal(null);

    setup() {
        this.state = proxy({});
        this.updateState();

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
            onClose: () => {
                if (!this.props.config.editor.isDestroyed) {
                    this.updateState();
                }
            },
            withScope: true,
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
        this.popover.open(this.root(), {
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
