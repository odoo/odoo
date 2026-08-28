import { Component, useProps, t } from "@odoo/owl";

export class HeaderTopOptions extends Component {
    static template = "website.HeaderTopOptions";
    props = useProps({
        openEditMenu: t.function(),
    });
}
