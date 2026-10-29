/** @odoo-module */

import { MockEventTarget } from "../hoot_utils";
import { MockMessageChannel } from "./network";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { AudioContext: $AudioContext, DOMException, Event, OfflineAudioContext, Set } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {string} message
 */
function invalidState(message) {
    return new DOMException(message, "InvalidStateError");
}

/** @type {AudioContext | null} */
let silentContext = null;
/** @type {Set<MediaStreamTrack>} */
const silentTracks = new Set();

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupWebAudio() {
    for (const track of silentTracks) {
        track.stop();
    }
    silentTracks.clear();
    silentContext?.close();
    silentContext = null;
}

/**
 * Returns a stream holding a real audio track, which can thus be used by other
 * native APIs (e.g. `MediaStream` or `RTCPeerConnection`). It produces silence
 * from a native context which is not rendered to any output device.
 */
export function createSilentAudioStream() {
    silentContext ||= new $AudioContext({ sinkId: { type: "none" } });
    const { stream } = silentContext.createMediaStreamDestination();
    for (const track of stream.getTracks()) {
        silentTracks.add(track);
    }
    return stream;
}

/**
 * Inert audio node: connecting nodes does not process any audio.
 */
export class MockAudioNode extends MockEventTarget {
    channelCount = 2;
    numberOfInputs = 1;
    numberOfOutputs = 1;

    /**
     * @param {MockAudioContext} context
     * @param {AudioNodeOptions} [options]
     */
    constructor(context, options) {
        super(...arguments);

        this.context = context;
        this.channelCount = options?.channelCount ?? this.channelCount;
    }

    /**
     * @template {MockAudioNode | MockAudioParam} T
     * @param {T} destination
     * @returns {T}
     */
    connect(destination) {
        return destination;
    }

    disconnect() {}
}

export class MockAnalyserNode extends MockAudioNode {
    fftSize = 2048;
    maxDecibels = -30;
    minDecibels = -100;
    smoothingTimeConstant = 0.8;

    /**
     * @param {MockAudioContext} context
     * @param {AnalyserOptions} [options]
     */
    constructor(context, options) {
        super(...arguments);

        for (const key of ["fftSize", "maxDecibels", "minDecibels", "smoothingTimeConstant"]) {
            this[key] = options?.[key] ?? this[key];
        }
    }

    get frequencyBinCount() {
        return this.fftSize / 2;
    }

    /**
     * @param {Uint8Array} array
     */
    getByteFrequencyData(array) {
        array.fill(0);
    }

    /**
     * @param {Uint8Array} array
     */
    getByteTimeDomainData(array) {
        array.fill(128);
    }

    /**
     * @param {Float32Array} array
     */
    getFloatFrequencyData(array) {
        array.fill(-Infinity);
    }

    /**
     * @param {Float32Array} array
     */
    getFloatTimeDomainData(array) {
        array.fill(0);
    }
}

export class MockAudioBufferSourceNode extends MockAudioNode {
    static publicListeners = ["ended"];

    /** @type {AudioBuffer | null} */
    buffer = null;
    loop = false;
    numberOfInputs = 0;
    playbackRate = new MockAudioParam(1);

    start() {}

    stop() {
        this.dispatchEvent(new Event("ended"));
    }
}

export class MockAudioContext extends MockEventTarget {
    static publicListeners = ["statechange"];

    audioWorklet = { addModule: async () => {} };
    baseLatency = 0;
    currentTime = 0;
    destination = new MockAudioNode(this);
    sampleRate = 44100;
    /** @type {AudioContextState} */
    state = "suspended";

    /**
     * @param {AudioContextOptions} [options]
     */
    constructor(options) {
        super(...arguments);

        this.sampleRate = options?.sampleRate ?? this.sampleRate;
    }

    async close() {
        if (this.state === "closed") {
            throw invalidState("Cannot close a closed AudioContext");
        }
        this._setState("closed");
    }

    createAnalyser() {
        return new MockAnalyserNode(this);
    }

    createBufferSource() {
        return new MockAudioBufferSourceNode(this);
    }

    createGain() {
        return new MockGainNode(this);
    }

    createMediaStreamDestination() {
        return new MockMediaStreamAudioDestinationNode(this);
    }

    /**
     * @param {MediaStream} mediaStream
     */
    createMediaStreamSource(mediaStream) {
        return new MockMediaStreamAudioSourceNode(this, { mediaStream });
    }

    /**
     * @param {number} [bufferSize]
     */
    createScriptProcessor(bufferSize = 4096) {
        return new MockScriptProcessorNode(this, bufferSize);
    }

    /**
     * Audio data is actually decoded (by an offline context, which does not
     * hold any audio device).
     *
     * @param {ArrayBuffer} audioData
     */
    async decodeAudioData(audioData) {
        return new OfflineAudioContext(1, 1, this.sampleRate).decodeAudioData(audioData);
    }

    async resume() {
        if (this.state === "closed") {
            throw invalidState("Cannot resume a closed AudioContext");
        }
        this._setState("running");
    }

    async suspend() {
        if (this.state === "closed") {
            throw invalidState("Cannot suspend a closed AudioContext");
        }
        this._setState("suspended");
    }

    /**
     * @private
     * @param {AudioContextState} state
     */
    _setState(state) {
        if (this.state !== state) {
            this.state = state;
            this.dispatchEvent(new Event("statechange"));
        }
    }
}

export class MockAudioParam {
    /**
     * @param {number} defaultValue
     * @param {number} [value]
     */
    constructor(defaultValue, value = defaultValue) {
        this.defaultValue = defaultValue;
        this.value = value;
    }

    /**
     * @param {number} value
     */
    setValueAtTime(value) {
        this.value = value;
        return this;
    }
}

export class MockAudioWorkletNode extends MockAudioNode {
    static publicListeners = ["processorerror"];

    parameters = new Map();
    port = new MockMessageChannel().port1;
}

export class MockGainNode extends MockAudioNode {
    /**
     * @param {MockAudioContext} context
     * @param {GainOptions} [options]
     */
    constructor(context, options) {
        super(...arguments);

        this.gain = new MockAudioParam(1, options?.gain);
    }
}

export class MockMediaStreamAudioDestinationNode extends MockAudioNode {
    numberOfOutputs = 0;
    stream = createSilentAudioStream();
}

export class MockMediaStreamAudioSourceNode extends MockAudioNode {
    numberOfInputs = 0;

    /**
     * @param {MockAudioContext} context
     * @param {{ mediaStream: MediaStream }} options
     */
    constructor(context, { mediaStream }) {
        if (!mediaStream.getAudioTracks().length) {
            throw invalidState("MediaStream has no audio track");
        }

        super(...arguments);

        this.mediaStream = mediaStream;
    }
}

export class MockScriptProcessorNode extends MockAudioNode {
    static publicListeners = ["audioprocess"];

    /**
     * @param {MockAudioContext} context
     * @param {number} bufferSize
     */
    constructor(context, bufferSize) {
        super(...arguments);

        this.bufferSize = bufferSize;
    }
}
