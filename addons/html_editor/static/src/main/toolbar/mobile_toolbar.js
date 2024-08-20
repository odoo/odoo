import { Component, onMounted, useExternalListener, useRef } from "@odoo/owl";
import { Toolbar } from "./toolbar";

export class ToolbarMobile extends Component {
    static template = "html_editor.MobileToolbar";
    static props = ["*"];
    static components = {
        Toolbar,
    };

    setup() {
        this.toolbar = useRef("toolbarWrapper");
        useExternalListener(window.visualViewport, "resize", this.fixToolbarPosition);
        onMounted(() => {
            this.fixToolbarPosition();
        });
    }

    /**
     * Fixes the position of the toolbar for the keyboard height.
     */
    fixToolbarPosition() {
        const keyboardHeight = window.innerHeight - window.visualViewport.height;
        if (keyboardHeight > 0) {
            this.toolbar.el.style.bottom = `${keyboardHeight}px`;
        } else {
            this.toolbar.el.style.bottom = `0px`;
        }
    }
}
