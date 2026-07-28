import { Component, signal, t, useProps } from "@odoo/owl";

export class EmbeddedComponentToolbar extends Component {
    static props = {
        buttonsGroupClass: { type: String, optional: true },
        slots: Object,
    };
    static template = "html_editor.EmbeddedComponentToolbar";
}

export class EmbeddedComponentToolbarButton extends Component {
    static props = {
        buttonRef: { type: Function, optional: true }, // signal ref owned by the parent
        hidden: { type: Boolean, optional: true },
        icon: { type: String, optional: true },
        icon_class: { type: String, optional: true },
        label: String,
        name: { type: String, optional: true },
        onClick: Function,
        title: { type: String, optional: true },
    };
    static template = "html_editor.EmbeddedComponentToolbarButton";

    buttonRef = useProps.static(
        "buttonRef",
        t.signal(t.ref()).optional(() => signal.ref())
    );
}
