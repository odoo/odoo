import { Component, props, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { WebrtcDebugPopup } from "@point_of_sale/app/components/popups/webrtc_debug_popup/webrtc_debug_popup";

export class WebrtcDebugButton extends Component {
    static template = "point_of_sale.WebrtcDebugButton";
    props = props({ webrtc: t.object() });

    setup() {
        this.dialog = useService("dialog");
    }

    open() {
        this.dialog.add(WebrtcDebugPopup, { webrtc: this.props.webrtc });
    }
}
