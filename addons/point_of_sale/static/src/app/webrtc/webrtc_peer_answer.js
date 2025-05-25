import enhancedConsole from "../utils/enhanced_console";

/**
 * This function is called when a new ICE candidate is received from the server.
 * It adds the candidate to the peer connection.
 *
 * @param {Object} orm - The ORM instance to call the server.
 * @param {Object} peer - The WebRTCPeer instance that will handle the candidate.
 * @param {Object} message - The message containing the offer data.
 */
export async function webRTCPeerAnswer({ orm, peer, message }) {
    try {
        await peer.peer.setRemoteDescription(message.data.data);
        const answer = await peer.peer.createAnswer();
        await peer.peer.setLocalDescription(answer);
        await orm.call("pos.config", "webrtc_signal", [
            odoo.pos_config_id,
            odoo.login_number,
            {
                data: answer,
                identifier: message.data.identifier,
            },
        ]);
        enhancedConsole("info", "WEBRTC", `${peer.id} - Answer sent`);
    } catch {
        enhancedConsole(
            "error",
            "WEBRTC",
            `${peer.id} - Error setting remote description or answering`
        );
    }
}

/**
 * This function is called when a peer receives an answer from another peer.
 * It sets the remote description for the peer connection.
 *
 * @param {Object} peer - The WebRTCPeer instance that will handle the answer.
 * @param {Object} message - The message containing the answer data.
 */
export async function webRTCHandlePeerAnswer({ peer, message }) {
    try {
        await peer.peer.setRemoteDescription(message.data.data);
        enhancedConsole("success", "WEBRTC", `${peer.id} - Answer set`);
    } catch (error) {
        enhancedConsole(
            "error",
            "WEBRTC",
            `${peer.id} - Error setting remote description for answer`,
            error
        );
    }
}
