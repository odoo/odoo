/**
 * Allows to use both peer to peer and SFU connections simultaneously, which makes it possible to
 * establish a connection with other call participants with the SFU when possible, and still handle
 * peer-to-peer for the participants who did not manage to establish a SFU connection.
 */
export class Network {
    /** @type {import("@mail/discuss/call/common/peer_to_peer").PeerToPeer} */
    p2p;
    /** @type {import("@mail/../lib/odoo_sfu/odoo_sfu").SfuClient} */
    sfu;
    /** @type {[{ name: string, f: EventListener }]} */
    _listeners = [];
    /**
     * @param {import("@mail/discuss/call/common/peer_to_peer").PeerToPeer} p2p
     * @param {import("@mail/../lib/odoo_sfu/odoo_sfu").SfuClient} [sfu]
     */
    constructor(p2p, sfu) {
        this.p2p = p2p;
        this.sfu = sfu;
    }

    /**
     * @param sessionId
     * @returns {{ type: StreamType, state: string }[]}
     */
    getSfuConsumerStats(sessionId) {
        const consumers = this.sfu?._consumers.get(sessionId);
        if (!consumers) {
            return [];
        }
        return Object.entries(consumers).map(([type, consumer]) => {
            let state = "active";
            if (!consumer) {
                state = "no consumer";
            } else if (consumer.closed) {
                state = "closed";
            } else if (consumer.paused) {
                state = "paused";
            } else if (!consumer.track) {
                state = "no track";
            } else if (!consumer.track.enabled) {
                state = "track disabled";
            } else if (consumer.track.muted) {
                state = "track muted";
            }
            return { type, state };
        });
    }

    /**
     * add a SFU to the network.
     * @param {import("@mail/../lib/odoo_sfu/odoo_sfu").SfuClient} sfu
     */
    addSfu(sfu) {
        if (this.sfu) {
            this.sfu.disconnect();
        }
        this.sfu = sfu;
    }
    removeSfu() {
        if (!this.sfu) {
            return;
        }
        for (const { name, f } of this._listeners) {
            this.sfu.removeEventListener(name, f);
        }
        this.sfu.disconnect();
    }
    /**
     * @param {string} name
     * @param {function} f
     * @override
     */
    addEventListener(name, f) {
        this._listeners.push({ name, f });
        this.p2p.addEventListener(name, f);
        this.sfu?.addEventListener(name, f);
    }
    /**
     * @param {StreamType} type
     * @param {MediaStreamTrack | null} track track to be sent to the other call participants,
     * not setting it will remove the track from the server
     */
    async updateUpload(type, track) {
        await Promise.all([
            this.sfu?.state === "connected" && this.sfu.updateUpload(type, track),
            this.p2p.updateUpload(type, track),
        ]);
    }
    /**
     * Stop or resume the consumption of tracks from the other call participants.
     *
     * @param {number} sessionId
     * @param {DownloadStates} states e.g: { audio: true, camera: false }
     */
    updateDownload(sessionId, states) {
        this.p2p.updateDownload(sessionId, states);
        this.sfu?.updateDownload(sessionId, states);
    }
    /**
     * Updates the server with the info of the session (isTalking, isCameraOn,...) so that it can broadcast it to the
     * other call participants.
     *
     * @param {import("@mail/discuss/call/common/rtc_session_model").SessionInfo} info
     * @param {Object} [options] see documentation of respective classes
     */
    updateInfo(info, options = {}) {
        this.p2p.updateInfo(info);
        this.sfu?.updateInfo(info, options);
    }
    disconnect() {
        for (const { name, f } of this._listeners.splice(0)) {
            this.p2p.removeEventListener(name, f);
            this.sfu?.removeEventListener(name, f);
        }
        this.p2p.disconnect();
        this.sfu?.disconnect();
    }
}
