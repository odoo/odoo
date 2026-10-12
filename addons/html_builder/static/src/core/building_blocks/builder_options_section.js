import { Component, useProps, t } from "@odoo/owl";

export class BuilderOptionsSection extends Component {
    static template = "html_builder.BuilderOptionsSection";
    props = useProps({
        title: t.string().optional(),
        containerClass: t.string().optional(),
        slots: t.object().optional(),
    });
}
