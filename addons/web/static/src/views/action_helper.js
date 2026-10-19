import { Component, t, useProps } from "@odoo/owl";

export class ActionHelper extends Component {
    static template = "web.ActionHelper";
    props = useProps({
        noContentHelp: t.string().optional(),
    });

    get showDefaultHelper() {
        return !this.props.noContentHelp;
    }
}
