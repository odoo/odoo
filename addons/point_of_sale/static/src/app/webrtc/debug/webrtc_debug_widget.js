import { Component, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { WebrtcDebugPopup } from "@point_of_sale/app/webrtc/debug/webrtc_debug_popup";

export class WebrtcDebugWidget extends Component {
    static template = "point_of_sale.WebrtcDebugWidget";
    props = useProps({ besideDebugWidget: t.boolean().optional(false) });

    setup() {
        this.dialog = useService("dialog");
    }

    open() {
        this.dialog.add(WebrtcDebugPopup);
    }
}
