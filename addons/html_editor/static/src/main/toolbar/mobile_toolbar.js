import { Component, onMounted, signal, t, useListener, useProps } from "@odoo/owl";
import { Toolbar } from "./toolbar";

export class ToolbarMobile extends Component {
    static components = {
        Toolbar,
    };
    static template = "html_editor.MobileToolbar";

    props = useProps({
        class: t.string().optional(),
        editable: t.customValidator(t.object(), (el) => el.nodeType === Node.ELEMENT_NODE),
        focusEditable: t.function(),
        getSelection: t.function(),
        state: t.object(),
    });

    toolbarRef = signal.ref();

    setup() {
        try {
            const innerWindow = this.props.editable.ownerDocument.defaultView;
            const frameElement = innerWindow.frameElement;
            this.targetWindow = frameElement?.ownerDocument.defaultView ?? window;
        } catch {
            // iframe origin or sandbox restriction
            this.targetWindow = window;
        }
        useListener(this.targetWindow.visualViewport, "resize", this.fixToolbarPosition.bind(this));
        useListener(this.targetWindow.visualViewport, "scroll", this.fixToolbarPosition.bind(this));

        onMounted(() => this.fixToolbarPosition());
    }

    /**
     * Fixes the position of the toolbar for the keyboard height.
     */
    fixToolbarPosition() {
        const el = this.toolbarRef();
        if (!el) {
            return;
        }
        const visualViewport = this.targetWindow.visualViewport;
        const keyboardHeight = Math.max(
            0,
            this.targetWindow.innerHeight - (visualViewport.height + visualViewport.offsetTop)
        );

        el.style.bottom = `${keyboardHeight}px`;
    }
}
