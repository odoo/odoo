import { Component, signal, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useAutofocus } from "@web/core/utils/hooks";

export class AccessibilityDialog extends Component {
    static template = "html_editor.AccessibilityDialog";
    static components = { Dialog };
    closeButtonRef = signal.ref();
    props = useProps({
        shortcuts: t.array(t.object()),
        shorthands: t.array(t.object()),
        close: t.function(),
    });

    setup() {
        useAutofocus({ ref: this.closeButtonRef, mobile: true });
    }
}
