import { Record } from "@mail/core/common/record";

const MESSAGE_TYPE = {
    REQUEST: "REQUEST",
    SYNC: "SYNC",
};

export class CallSyncState extends Record {
    // TODO are these statics necessary?
    static id = "id";
    /** @type {Object.<number, CallSyncState>} */
    static records = {};

    /** @type {BroadcastChannel} */
    _broadcastChannel = new BroadcastChannel("call_sync_state");
    _remotelyHostedChannel;
    rtc = Record.one("Rtc", {
        inverse: "syncState",
        onDelete() {
            this.delete();
        },
    });

    get channel() {
        return this.rtc.state.channel || this._remotelyHostedChannel;
    }

    get selfSession() {
        return this.rtc.selfSession;
    }

    get isHost() {
        return Boolean(this.selfSession);
    }

    get isMute() {
        return this.isMuted || this.isDeaf;
    }

    // STATE
    _isMuted;
    get isMuted() {
        return this.selfSession?.is_muted ?? this._isMuted;
    }
    _isDeaf;
    get isDeaf() {
        return this.selfSession?.is_deaf ?? this._isDeaf;
    }
    _isCameraOn;
    get isCameraOn() {
        return this.selfSession?.is_camera_on ?? this._isCameraOn;
    }
    _isScreenSharingOn;
    get isScreenSharingOn() {
        return this.selfSession?.is_screen_sharing_on ?? this._isScreenSharingOn;
    }
    _raisingHand;
    get raisingHand() {
        return this.selfSession?.raisingHand ?? this._raisingHand;
    }

    setup() {
        super.setup();
        if (!this._broadcastChannel) {
            return;
        }
        this._broadcastChannel.onmessage = this._onMessage.bind(this);
        this._post({ type: MESSAGE_TYPE.REQUEST });
    }
    async _onMessage({ data: { type, hostedChannelId, changes } }) {
        switch (type) {
            case MESSAGE_TYPE.REQUEST: {
                if (!this.isHost) {
                    return;
                }
                await this._apply(changes);
                this._share();
                return;
            }
            case MESSAGE_TYPE.SYNC: {
                if (this.isHost) {
                    return;
                }
                this._remotelyHostedChannel = this.store.Thread.getOrFetch({
                    model: "discuss.channel",
                    id: hostedChannelId,
                });
                await this._sync(changes);
                return;
            }
        }
    }
    async apply(changes) {
        if (this.isHost) {
            await this._apply(changes);
            this._share();
            return;
        }
        this._requestApply(changes);
    }

    _requestApply(changes) {
        this._post({ type: MESSAGE_TYPE.REQUEST, changes });
    }

    _sync(changes) {
        const rtcSessions = changes.rtcSessions;
        console.log("TODO update rtc sessions of this.channel with:", rtcSessions);
        delete changes.rtcSessions;
        for (const [key, value] of Object.entries(changes)) {
            this[`_${key}`] = value;
        }
    }

    async _apply(changes) {
        const promises = [];
        for (const [key, value] of Object.entries(changes)) {
            switch (key) {
                case "isMuted":
                    if (value === this.isMuted) {
                        break;
                    }
                    value ? this.rtc.mute() : this.rtc.unmute();
                    break;
                case "isDeaf":
                    if (value === this.isDeaf) {
                        break;
                    }
                    value ? promises.push(this.rtc.deafen()) : promises.push(this.rtc.undeafen());
                    break;
                case "isCameraOn":
                    if (value === this.isCameraOn) {
                        break;
                    }
                    promises.push(this.rtc.toggleVideo("camera", value));
                    break;
                case "isScreenSharingOn":
                    if (value === this.isScreenSharingOn) {
                        break;
                    }
                    promises.push(this.rtc.toggleVideo("screen", value));
                    break;
                case "raisingHand":
                    if (value === this.raisingHand) {
                        break;
                    }
                    promises.push(this.rtc.raiseHand(value));
                    break;
            }
        }
        await Promise.all(promises);
    }

    _share() {
        this._post({
            type: MESSAGE_TYPE.SYNC,
            hostedChannelId: this.channel.id,
            payload: {
                rtcSessions: [],
                isMuted: this.isMuted,
                isDeaf: this.isDeaf,
                isCameraOn: this.isCameraOn,
                isScreenSharingOn: this.isScreenSharingOn,
                raisingHand: this.raisingHand,
            },
        });
    }

    _post(message) {
        this._broadcastChannel?.postMessage(message);
    }
}

CallSyncState.register();
