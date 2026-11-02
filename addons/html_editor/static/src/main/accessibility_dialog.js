import { Component, signal, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useAutofocus } from "@web/core/utils/hooks";

export class AccessibilityDialog extends Component {
    static template = "html_editor.AccessibilityDialog";
    static components = { Dialog };
    props = useProps({
        shortcuts: t.array(t.object()),
        shorthands: t.array(t.object()),
        close: t.function(),
    });
    closeButton = signal.ref();

    setup() {
        useAutofocus({ ref: this.closeButton, mobile: true });
    }
}
