import { Record } from "@mail/core/common/record";

const HOST_MESSAGE = {
    SESSION_INFO_CHANGE: "SESSION_INFO_CHANGE", // sent with updated state of the remote rtc sessions of the call
    SYNC_CONTROLS: "SYNC_CONTROLS", // sent with the updated state of controls
    CLOSE: "CLOSE", // sent when the host ends the call
};

const CLIENT_MESSAGE = {
    CONTROL_CHANGE: "CONTROL_CHANGE", // request to change a control (mute, deaf,...)
    LEAVE: "LEAVE", // request to leave call
};

export class CallSyncState extends Record {
    // TODO are these statics necessary?
    static id = "id";
    /** @type {Object.<number, CallSyncState>} */
    static records = {};

    /** @type {BroadcastChannel} */
    _broadcastChannel = new BroadcastChannel("call_sync_state");
    _hostId;
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

    get isRemote() {
        // TODO show message on call view if remote (this call is hosted on another tab).
        return Boolean(this._remotelyHostedChannel);
    }

    get isHost() {
        return Boolean(this.selfSession);
    }

    // STATE
    get isMute() {
        return this.isMuted || this.isDeaf;
    }
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

    start() {
        if (!this._broadcastChannel) {
            return;
        }
        this._broadcastChannel.onmessage = this._onMessage.bind(this);
        this._post({ type: CLIENT_MESSAGE.CONTROL_CHANGE });
    }
    host() {
        this._hostId = this.selfSession.id;
        this._remotelyHostedChannel = undefined;
        this._share();
    }
    endHost() {
        this._post({ type: HOST_MESSAGE.CLOSE, hostId: this._hostId });
    }

    toggleCall(channel) {
        if (channel.eq(this._remotelyHostedChannel)) {
            this._post({ type: CLIENT_MESSAGE.LEAVE });
        } else {
            this.rtc.toggleCall(...arguments);
        }
    }

    updateSessionInfo(changes) {
        if (!this.isHost) {
            return;
        }
        this.rtc.updateSessionInfo(changes);
        this._post({ type: HOST_MESSAGE.SESSION_INFO_CHANGE, changes });
    }

    async _onMessage({ data: { type, hostedChannelId, originSessionId, changes } }) {
        switch (type) {
            case HOST_MESSAGE.SESSION_INFO_CHANGE:
                if (this.isHost) {
                    return;
                }
                this.rtc.updateSessionInfo(changes);
                return;
            case CLIENT_MESSAGE.CONTROL_CHANGE: {
                if (!this.isHost) {
                    return;
                }
                await this._localApply(changes);
                this._share();
                return;
            }
            case HOST_MESSAGE.SYNC_CONTROLS: {
                if (this.isHost) {
                    return;
                }
                this._hostId = originSessionId;
                this._remotelyHostedChannel = await this.store.Thread.getOrFetch({
                    model: "discuss.channel",
                    id: hostedChannelId,
                });
                await this._sync(changes);
                return;
            }
            case HOST_MESSAGE.CLOSE: {
                if (this._hostId !== originSessionId) {
                    return;
                }
                this._remotelyHostedChannel = null;
                this._hostId = undefined;
                return;
            }
            case CLIENT_MESSAGE.LEAVE: {
                if (!this.isHost) {
                    return;
                }
                await this.rtc.leaveCall(this.channel);
            }
        }
    }
    async command(changes) {
        if (this.isHost) {
            await this._localApply(changes);
            this._share();
            return;
        }
        this._remoteApply(changes);
    }

    _remoteApply(changes) {
        this._post({ type: CLIENT_MESSAGE.CONTROL_CHANGE, changes });
    }

    _sync(changes = {}) {
        for (const [key, value] of Object.entries(changes)) {
            this[`_${key}`] = value;
        }
    }

    async _localApply(changes = {}) {
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
            type: HOST_MESSAGE.SYNC_CONTROLS,
            hostedChannelId: this.channel.id,
            originSessionId: this.selfSession.id,
            changes: {
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
