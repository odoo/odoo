import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(ListRenderer.prototype, {

    /**
     * Generates the unique identifier for subscribing to WebSocket
     * @returns {string} Unique identifier for subscription
     */
    _getMergedViewIdentifier() {
        return `bus.listener.mixin/create_${this.props.list.resModel}_${this.env.config.viewId}`;
    },

    setup() {
        super.setup(...arguments);

        this.busService = useService('bus_service');
        this.busService.subscribe(this._getMergedViewIdentifier(), this._onWebSocketMessage.bind(this));

        onWillUnmount(() => {
            this._unsubscribeFromWebSocket();
        });
    },

    /**
     * Logic for handling WebSocket messages
     * @param {Object} message Data received from the WebSocket
     */
    _onWebSocketMessage(message) {
        if (message.mergedView === this._getMergedViewIdentifier()) {
            this.env.searchModel._notify();
        }
    },

    /**
     * Securely unsubscribing from the WebSocket event
     */
    _unsubscribeFromWebSocket() {
        if (this.busService && typeof this.busService.unsubscribe === "function") {
            this.busService.unsubscribe(this._getMergedViewIdentifier());
        }
    }
});

