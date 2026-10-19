import { Component, t, useProps } from "@odoo/owl";

export class Tooltip extends Component {
    static template = "web.Tooltip";
    props = useProps({
        close: t.function(),
        tooltip: t.string().optional(),
        template: t.string().optional(),
        info: t.any().optional(),
    });
}
