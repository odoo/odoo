import { Component, t, useProps } from "@odoo/owl";

export class InfoPopup extends Component {
    static template = "pos_self_order.InfoPopup";
    props = useProps({
        text: t.string(),
        close: t.function(),
        buttons: t.array(t.object({ text: t.string(), onClick: t.function() })),
    });
}
