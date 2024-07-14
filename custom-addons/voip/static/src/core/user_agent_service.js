/* @odoo-module */
/* global SIP */

import { reactive } from "@odoo/owl";

import { Registerer } from "@voip/core/registerer";
import { cleanPhoneNumber } from "@voip/utils/utils";

import { getBundle, loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

/**
 * @typedef Session
 * @property {"trying"|"ringing"|"ok"} [inviteState]
 * @property {boolean} isMute
 * @property {import("@voip/core/call_model").Call} call
 * @property {window.sip.Session} [sipSession]
 * @property {string} [transferTarget]
 */

export class UserAgent {
    attemptingToReconnect = false;
    /**
     * The id of the setTimeout used in demo mode to simulate the waiting time
     * before the call is picked up.
     *
     * @type {number}
     */
    demoTimeout;
    preferredInputDevice;
    registerer;
    /**
     * The Audio element used to play the audio stream received from the remote
     * call party.
     *
     * @type {HTMLAudioElement}
     */
    remoteAudio = new window.Audio();
    /**
     * @type {Session}
     */
    session;
    transferTarget;
    voip;
    __sipJsUserAgent;

    constructor(env, services) {
        this.env = env;
        this.callService = services["voip.call"];
        this.notificationService = services.notification;
        this.ringtoneService = services["voip.ringtone"];
        this.voip = services.voip;
        this.softphone = this.voip.softphone;
        this.voip.isReady.then(() => this.init());
        return reactive(this);
    }

    /** @returns {Object} */
    get mediaConstraints() {
        const constraints = { audio: true, video: false };
        if (this.preferredInputDevice) {
            constraints.audio = { deviceId: { exact: this.preferredInputDevice } };
        }
        return constraints;
    }

    /**
     * Provides the function that will be used by the SIP.js library to create
     * the media source that will serve as the local media stream (i.e. the
     * recording of the user's microphone).
     *
     * @returns {SIP.MediaStreamFactory}
     */
    get mediaStreamFactory() {
        return (constraints, sessionDescriptionHandler) => {
            const mediaRequest = browser.navigator.mediaDevices.getUserMedia(constraints);
            mediaRequest.then(
                (stream) => this._onGetUserMediaSuccess(stream),
                (error) => this._onGetUserMediaFailure(error)
            );
            return mediaRequest;
        };
    }

    /**
     * Provides the handlers to be called by the SIP.js library when receiving
     * SIP requests (BYE, INFO, ACK, REFER…).
     *
     * @returns {SIP.SessionDelegate}
     */
    get sessionDelegate() {
        return { onBye: (bye) => this._onBye(bye) };
    }

    /** @returns {Object} */
    get sipJsUserAgentConfig() {
        const isDebug = odoo.debug !== "";
        return {
            authorizationPassword: this.voip.settings.voip_secret,
            authorizationUsername: this.voip.authorizationUsername,
            delegate: {
                onDisconnect: (error) => this._onTransportDisconnected(error),
                onInvite: (inviteSession) => this._onIncomingInvitation(inviteSession),
            },
            hackIpInContact: true,
            logBuiltinEnabled: isDebug,
            logLevel: isDebug ? "debug" : "error",
            sessionDescriptionHandlerFactory: SIP.Web.defaultSessionDescriptionHandlerFactory(
                this.mediaStreamFactory
            ),
            sessionDescriptionHandlerFactoryOptions: { iceGatheringTimeout: 1000 },
            transportOptions: {
                server: this.voip.webSocketUrl,
                traceSip: isDebug,
            },
            uri: SIP.UserAgent.makeURI(
                `sip:${this.voip.settings.voip_username}@${this.voip.pbxAddress}`
            ),
            userAgentString: `Odoo ${odoo.info.server_version} SIP.js/${window.SIP.version}`,
        };
    }

    async acceptIncomingCall() {
        this.ringtoneService.stopPlaying();
        this.session.sipSession.accept({
            sessionDescriptionHandlerOptions: {
                constraints: this.mediaConstraints,
            },
        });
        this.voip.triggerError(_t("Please accept the use of the microphone."));
    }

    async attemptReconnection(attemptCount = 0) {
        if (attemptCount > 5) {
            this.voip.triggerError(
                _t("The WebSocket connection was lost and couldn't be reestablished.")
            );
            return;
        }
        if (this.attemptingToReconnect) {
            return;
        }
        this.attemptingToReconnect = true;
        try {
            await this.__sipJsUserAgent.reconnect();
            this.registerer.register();
            this.voip.resolveError();
        } catch {
            setTimeout(
                () => this.attemptReconnection(attemptCount + 1),
                2 ** attemptCount * 1000 + Math.random() * 500
            );
        } finally {
            this.attemptingToReconnect = false;
        }
    }

    /**
     * @param {string} phoneNumber
     * @returns {SIP.URI}
     */
    getUri(phoneNumber) {
        const sanitizedNumber = cleanPhoneNumber(phoneNumber);
        return SIP.UserAgent.makeURI(`sip:${sanitizedNumber}@${this.voip.pbxAddress}`);
    }

    async hangup({ activityDone = true } = {}) {
        this.ringtoneService.stopPlaying();
        browser.clearTimeout(this.demoTimeout);
        if (this.session.sipSession) {
            this._cleanUpRemoteAudio();
            switch (this.session.sipSession.state) {
                case SIP.SessionState.Establishing:
                    this.session.sipSession.cancel();
                    break;
                case SIP.SessionState.Established:
                    this.session.sipSession.bye();
                    break;
            }
        }
        switch (this.session.call.state) {
            case "calling":
                await this.callService.abort(this.session.call);
                break;
            case "ongoing":
                await this.callService.end(this.session.call, { activityDone });
                break;
        }
        this.session = null;
        if (this.softphone.isInAutoCallMode) {
            this.softphone.selectNextActivity();
        }
    }

    async init() {
        if (this.voip.mode !== "prod") {
            return;
        }
        if (!this.voip.hasRtcSupport) {
            this.voip.triggerError(
                _t(
                    "Your browser does not support some of the features required for VoIP to work. Please try updating your browser or using a different one."
                )
            );
            return;
        }
        if (!this.voip.isServerConfigured) {
            this.voip.triggerError(
                _t("PBX or Websocket address is missing. Please check your settings.")
            );
            return;
        }
        if (!this.voip.areCredentialsSet) {
            this.voip.triggerError(
                _t("Your login details are not set correctly. Please contact your administrator.")
            );
            return;
        }
        try {
            await loadBundle(await getBundle("voip.assets_sip"));
        } catch (error) {
            console.error(error);
            this.voip.triggerError(
                _t("Failed to load the SIP.js library:\n\n%(error)s", {
                    error: error.message,
                })
            );
            return;
        }
        try {
            this.__sipJsUserAgent = new SIP.UserAgent(this.sipJsUserAgentConfig);
        } catch (error) {
            console.error(error);
            this.voip.triggerError(
                _t("An error occurred during the instantiation of the User Agent:\n\n%(error)s", {
                    error: error.message,
                })
            );
            return;
        }
        this.voip.triggerError(_t("Connecting…"));
        try {
            await this.__sipJsUserAgent.start();
        } catch {
            this.voip.triggerError(
                _t(
                    "The user agent could not be started. The websocket server URL may be incorrect. Please have an administrator check the websocket server URL in the General Settings."
                )
            );
            return;
        }
        this.registerer = new Registerer(this.voip, this.__sipJsUserAgent);
        this.registerer.register();
    }

    invite(phoneNumber) {
        let calleeUri;
        if (this.voip.willCallFromAnotherDevice) {
            calleeUri = this.getUri(this.voip.settings.external_device_number);
            this.session.transferTarget = phoneNumber;
        } else {
            calleeUri = this.getUri(phoneNumber);
        }
        try {
            const inviter = new SIP.Inviter(this.__sipJsUserAgent, calleeUri);
            inviter.delegate = this.sessionDelegate;
            inviter.stateChange.addListener((state) => this._onSessionStateChange(state));
            this.session.sipSession = inviter;
            this.session.sipSession.invite({
                requestDelegate: {
                    onAccept: (response) => this._onOutgoingInvitationAccepted(response),
                    onProgress: (response) => this._onOutgoingInvitationProgress(response),
                    onReject: (response) => this._onOutgoingInvitationRejected(response),
                },
                sessionDescriptionHandlerOptions: {
                    constraints: this.mediaConstraints,
                },
            }).catch((error) => {
                if (error.name === "NotAllowedError") {
                    return;
                }
                throw error;
            });
        } catch (error) {
            console.error(error);
            this.voip.triggerError(
                _t(
                    "An error occurred trying to invite the following number: %(phoneNumber)s\n\nError: %(error)s",
                    { phoneNumber, error: error.message }
                )
            );
        }
    }

    /** @param {Object} data */
    async makeCall(data) {
        if (!(await this.voip.willCallUsingVoip())) {
            window.location.assign(`tel:${data.phone_number}`);
            return;
        }
        const call = await this.callService.create(data);
        this.softphone.show();
        this.softphone.closeNumpad();
        this.notificationService.add(
            _t("Calling %(phone number)s", { "phone number": call.phoneNumber })
        );
        this.softphone.selectCorrespondence({ call });
        this.session = {
            inviteState: "trying",
            isMute: false,
            call,
        };
        this.ringtoneService.ringback.play();
        if (this.voip.mode === "prod") {
            this.invite(call.phoneNumber);
        } else {
            this.demoTimeout = browser.setTimeout(() => {
                this._onOutgoingInvitationAccepted();
            }, 3000);
        }
    }

    async rejectIncomingCall() {
        this.ringtoneService.stopPlaying();
        this.session.sipSession.reject({ statusCode: 603 /* Decline */ });
        await this.callService.reject(this.session.call);
        this.session = null;
    }

    /** @param {string} deviceId */
    async switchInputStream(deviceId) {
        if (!this.session.sipSession?.sessionDescriptionHandler.peerConnection) {
            return;
        }
        this.preferredInputDevice = deviceId;
        const stream = await browser.navigator.mediaDevices.getUserMedia(this.mediaConstraints);
        for (const sender of this.session.sipSession.sessionDescriptionHandler.peerConnection.getSenders()) {
            if (sender.track) {
                await sender.replaceTrack(stream.getAudioTracks()[0]);
            }
        }
    }

    /**
     * Transfers the call to the given number.
     *
     * @param {string} number
     */
    transfer(number) {
        if (this.voip.mode === "demo") {
            this.hangup();
            return;
        }
        const transferTarget = this.getUri(number);
        this.session.sipSession.refer(transferTarget, {
            requestDelegate: {
                onAccept: (response) => this._onReferAccepted(response),
            },
        });
    }

    updateSenderTracks() {
        if (!this.session?.sipSession?.sessionDescriptionHandler) {
            return;
        }
        const { peerConnection } = this.session.sipSession.sessionDescriptionHandler;
        for (const { track } of peerConnection.getSenders()) {
            if (track) {
                track.enabled = !this.session.isMute;
            }
        }
    }

    _cleanUpRemoteAudio() {
        this.remoteAudio.srcObject = null;
        this.remoteAudio.pause();
    }

    /**
     * Triggered when receiving a BYE request. Useful to detect when the callee
     * of an outgoing call hangs up.
     *
     * @param {SIP.IncomingByeRequest} bye
     */
    async _onBye({ incomingByeRequest: bye }) {
        if (!this.session) {
            return;
        }
        await this.callService.end(this.session.call);
        this.session = null;
        this._cleanUpRemoteAudio();
        if (this.softphone.isInAutoCallMode) {
            this.softphone.selectNextActivity();
        }
    }

    /** @param {DOMException} error */
    _onGetUserMediaFailure(error) {
        console.error(error);
        const errorMessage = (() => {
            switch (error.name) {
                case "NotAllowedError":
                    return _t(
                        "Cannot access audio recording device. If you have denied access to your microphone, please allow it and try again. Otherwise, make sure that this website is running over HTTPS and that your browser is not set to deny access to media devices."
                    );
                case "NotFoundError":
                    return _t(
                        "No audio recording device available. The application requires a microphone in order to be used."
                    );
                case "NotReadableError":
                    return _t(
                        "A hardware error has occurred while trying to access the audio recording device. Please ensure that your drivers are up to date and try again."
                    );
                default:
                    return _t(
                        "An error occured involving the audio recording device (%(errorName)s):\n%(errorMessage)s",
                        { errorMessage: error.message, errorName: error.name }
                    );
            }
        })();
        this.voip.triggerError(errorMessage, { isNonBlocking: true });
        if (this.session.call.direction === "outgoing") {
            this.hangup();
        } else {
            this.rejectIncomingCall();
        }
    }

    /** @param {MediaStream} stream */
    _onGetUserMediaSuccess(stream) {
        this.voip.resolveError();
        switch (this.session.call.direction) {
            case "outgoing":
                this.ringtoneService.dial.play();
                break;
            case "incoming":
                this.callService.start(this.session.call);
                break;
        }
    }

    /** @param {Object} inviteSession */
    async _onIncomingInvitation(inviteSession) {
        if (this.session) {
            inviteSession.reject({ statusCode: 486 /* Busy Here */ });
            return;
        }
        if (this.voip.settings.should_auto_reject_incoming_calls) {
            inviteSession.reject({ statusCode: 488 /* Not Acceptable Here */ });
            return;
        }
        const phoneNumber = inviteSession.remoteIdentity.uri.user;
        const call = await this.callService.create({
            direction: "incoming",
            phone_number: phoneNumber,
            state: "calling",
        });
        this.softphone.selectCorrespondence({ call });
        inviteSession.delegate = this.sessionDelegate;
        inviteSession.incomingInviteRequest.delegate = {
            onCancel: (message) => this._onIncomingInvitationCanceled(message),
        };
        inviteSession.stateChange.addListener((state) => this._onSessionStateChange(state));
        this.session = {
            call,
            isMute: false,
            sipSession: inviteSession,
        };
        this.softphone.show();
        this.ringtoneService.incoming.play();
        // TODO send notification
    }

    /**
     * Triggered when receiving CANCEL request.
     * Useful to handle missed phone calls.
     *
     * @param {SIP.IncomingRequestMessage} message
     */
    _onIncomingInvitationCanceled(message) {
        this.ringtoneService.stopPlaying();
        this.session.sipSession.reject({ statusCode: 487 /* Request Terminated */ });
        this.callService.miss(this.session.call);
        this.session = null;
    }

    /**
     * Triggered when receiving a 2xx final response to the INVITE request.
     *
     * @param {SIP.IncomingResponse} response
     * @param {function} response.ack
     * @param {SIP.IncomingResponseMessage} response.message
     * @param {SIP.SessionDialog} response.session
     */
    _onOutgoingInvitationAccepted(response) {
        this.ringtoneService.stopPlaying();
        this.session.inviteState = "ok";
        if (this.voip.willCallFromAnotherDevice) {
            this.transfer(this.session.transferTarget);
            return;
        }
        this.callService.start(this.session.call);
    }

    /**
     * Triggered when receiving a 1xx provisional response to the INVITE request
     * (excepted code 100 responses).
     *
     * NOTE: Relying on provisional responses to implement behaviors seems like
     * a bad idea, as they may or may not be sent depending on the SIP server
     * implementation.
     *
     * @param {SIP.IncomingResponse} response
     * @param {SIP.IncomingResponseMessage} response.message
     * @param {function} response.prack
     * @param {SIP.SessionDialog} response.session
     */
    _onOutgoingInvitationProgress(response) {
        const { statusCode } = response.message;
        if (statusCode === 183 /* Session Progress */ || statusCode === 180 /* Ringing */) {
            this.ringtoneService.ringback.play();
            this.session.inviteState = "ringing";
        }
    }

    /**
     * Triggered when receiving a 4xx, 5xx, or 6xx final response to the
     * INVITE request.
     *
     * @param {SIP.IncomingResponse} response
     * @param {SIP.IncomingResponseMessage} response.message
     * @param {number} response.message.statusCode
     * @param {string} response.message.reasonPhrase
     */
    _onOutgoingInvitationRejected(response) {
        this.ringtoneService.stopPlaying();
        if (response.message.statusCode === 487) { // Request Terminated
            // invitation has been cancelled by the user, the session has
            // already been terminated
            return;
        }
        const errorMessage = (() => {
            switch (response.message.statusCode) {
                case 404: // Not Found
                case 488: // Not Acceptable Here
                case 603: // Decline
                    return _t(
                        "The number is incorrect, the user credentials could be wrong or the connection cannot be made. Please check your configuration.\n(Reason received: %(reasonPhrase)s)",
                        { reasonPhrase: response.message.reasonPhrase }
                    );
                case 486: // Busy Here
                case 600: // Busy Everywhere
                    return _t("The person you try to contact is currently unavailable.");
                default:
                    return _t("Call rejected (reason: “%(reasonPhrase)s”)", {
                        reasonPhrase: response.message.reasonPhrase,
                    });
            }
        })();
        this.voip.triggerError(errorMessage, { isNonBlocking: true });
        this.callService.reject(this.session.call);
        this.session = null;
    }

    /**
     * Triggered when receiving a response with status code 2xx to the REFER
     * request.
     *
     * @param {SIP.IncomingResponse} response The server final response to the
     * REFER request.
     */
    _onReferAccepted(response) {
        this.session.sipSession.bye();
        this._cleanUpRemoteAudio();
        this.callService.end(this.session.call);
        this.session = null;
    }

    /** @param {SIP.SessionState} newState */
    _onSessionStateChange(newState) {
        switch (newState) {
            case SIP.SessionState.Initial:
                break;
            case SIP.SessionState.Establishing:
                break;
            case SIP.SessionState.Established:
                this._setUpRemoteAudio();
                this.session.sipSession.sessionDescriptionHandler.remoteMediaStream.onaddtrack = (
                    mediaStreamTrackEvent
                ) => this._setUpRemoteAudio();
                break;
            case SIP.SessionState.Terminating:
                break;
            case SIP.SessionState.Terminated:
                break;
            default:
                throw new Error(`Unknown session state: "${newState}".`);
        }
    }

    /**
     * Triggered when the transport transitions from connected state.
     *
     * @param {Error} error
     */
    _onTransportDisconnected(error) {
        if (!error) {
            return;
        }
        console.error(error);
        this.voip.triggerError(
            _t(
                "The websocket connection to the server has been lost. Attempting to reestablish the connection…"
            )
        );
        this.attemptReconnection();
    }

    _setUpRemoteAudio() {
        const remoteStream = new MediaStream();
        for (const receiver of this.session.sipSession.sessionDescriptionHandler.peerConnection.getReceivers()) {
            if (receiver.track) {
                remoteStream.addTrack(receiver.track);
                // According to the SIP.js documentation, this is needed by Safari to work.
                this.remoteAudio.load();
            }
        }
        this.remoteAudio.srcObject = remoteStream;
        this.remoteAudio.play();
    }
}

export const userAgentService = {
    dependencies: ["notification", "voip", "voip.call", "voip.ringtone"],
    start(env, services) {
        return new UserAgent(env, services);
    },
};

registry.category("services").add("voip.user_agent", userAgentService);
