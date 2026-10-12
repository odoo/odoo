import { Component, t, useProps } from "@odoo/owl";

export class ImportBlockUI extends Component {
    static template = "base_import.BlockUI";

    props = useProps({
        message: t.string().optional(),
        blockComponent: t.object().optional(),
    });
}
