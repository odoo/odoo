/** @odoo-module */

import { patch } from "@web/core/utils/patch";
// import { MockServer } from "@web/../tests/helpers/mock_server";
var MockServer = { prototype: {} };

patch(MockServer.prototype, {
    /**
     * @override
     */
    async _performRPC(route, args) {
        if (route === "/discuss/channel/fold") {
            return this._mockRouteDiscussChannelFold(args.channel_id, args.state, args.state_count);
        }
        return super._performRPC(route, args);
    },

    /**
     * Simulates the `/discuss/channel/fold` route.
     *
     * @param {number} channelId
     * @param {boolean} state
     * @param {number} stateCount
     */
    _mockRouteDiscussChannelFold(channelId, state, stateCount) {
        const memberOfCurrentUser = this._mockDiscussChannelMember__getAsSudoFromContext(channelId);
        return this._mockDiscussChannelMember__channelFold(
            memberOfCurrentUser.id,
            state,
            stateCount
        );
    },
});
