/* @odoo-module */

import { registry } from "@web/core/registry";

export class RtcServer {
    /** @type {string || undefined} */
    _url;
    /** @type {string || undefined} */
    _secret;
    /** @type {boolean} */
    canConnect = false;
    /** @type {boolean} */
    isConnected = false;
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.env = env;
    }

    /**
     * @param {object} serverInfo
     */
    async load(serverInfo) {
        if (serverInfo) {
            this._url = serverInfo.url;
            this._secret = serverInfo.secret;
            // AWAIT LAZY LOAD LIBRARY FROM _url/bundle.js; (mediasoup-client)
            this.canConnect = true;
        } else {
            this.canConnect = false;
        }
    }

    async connect() {
        try {
            // TODO should be this._url
            const splitUrl = location.origin.split(":");
            const capabilities = {}; // TODO https://mediasoup.org/documentation/v3/mediasoup-client/api/#device-rtpCapabilities
            splitUrl[2] = 8070;
            const url = splitUrl.join(":");
            const response = await fetch(`${url}/connect`, {
                body: JSON.stringify({
                    capabilities,
                    secret: this._secret,
                }),
                headers: {
                    "Content-Type": "application/json",
                },
                method: "POST",
            });
            // eslint-disable-next-line no-unused-vars
            const parsedResponse = await response.json();
            // TODO wait that ws and transports are really connected
            this.isConnected = true;
        } catch (e) {
            console.log(e);
        }
    }

    disconnectFromServer() {
        this.isConnected = false;
    }
}

export const rtcServerService = {
    dependencies: [],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new RtcServer(env, services);
    },
};

registry.category("services").add("discuss.rtc_server", rtcServerService);
