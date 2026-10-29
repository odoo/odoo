/** @odoo-module */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const { AudioContext: $AudioContext, Set } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

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
