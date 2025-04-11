import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {Function} removeWarningOverlay
 * @extends {Component<Props, Env>}
 */
export class ScreenshareWarningOverlay extends Component {
    static template = "discuss.ScreenshareWarningOverlay";
    static props = {
        removeWarningOverlay: { type: Function, required: true },
    };

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
    }

    stopSharing() {
        this.rtc.toggleVideo("screen", false);
        this.props.removeWarningOverlay();
    }

    ignore() {
        this.props.removeWarningOverlay();
    }
}
