import { Component, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { WebrtcDebugPopup } from "@point_of_sale/app/webrtc/debug/webrtc_debug_popup";

/**
 * Floating button opening the WebRTC debug popup, shown when the PoS is opened
 * with `?debug_webrtc=1`, next to the button of the regular debug widget if
 * the debug mode is active too.
 */
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
