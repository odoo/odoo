import enhancedConsole from "../utils/enhanced_console";

/**
 * This function is called when a new ICE candidate is received from the server.
 * It adds the candidate to the peer connection.
 *
 * @param {Object} peer - The WebRTCPeer instance that will handle the candidate.
 * @param {Object} message - The message containing the ICE candidate data.
 */
export async function webRTCPeerCandidate({ peer, message }) {
    try {
        await peer.peer.addIceCandidate(message.data.data);
        enhancedConsole("success", "WEBRTC", `${peer.id} - Ice candidate added`);
    } catch {
        enhancedConsole("red", "WEBRTC", `${peer.id} - Error adding ICE candidate`);
    }
}
