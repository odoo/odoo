import { Component, signal, t, useProps } from "@odoo/owl";

export class EmbeddedComponentToolbar extends Component {
    props = useProps({
        buttonsGroupClass: t.string().optional(),
        slots: t.object(),
    });
    static template = "html_editor.EmbeddedComponentToolbar";
}

export class EmbeddedComponentToolbarButton extends Component {
    props = useProps({
        buttonRef: t.function().optional(), // signal ref owned by the parent
        hidden: t.boolean().optional(),
        icon: t.string().optional(),
        iconClass: t.string().optional(),
        label: t.string(),
        name: t.string().optional(),
        onClick: t.function(),
        title: t.string().optional(),
    });
    static template = "html_editor.EmbeddedComponentToolbarButton";

    buttonRef = useProps.static(
        "buttonRef",
        t.signal(t.ref()).optional(() => signal.ref())
    );
}
