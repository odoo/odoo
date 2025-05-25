import enhancedConsole from "../utils/enhanced_console";

/**
 * This function is called up when the point of sale is initialized to create an offer
 * WebRTC connection. This offer will be sent to the server to be broadcast
 * to other peers.
 *
 * A peer will be created to generate the offer; this peer may sometimes remain inactive
 * if the point of sale is not in use. It is therefore important to manage the creation
 * and destruction of peers.
 *
 * @param {Object} orm - The ORM instance to call the server.
 * @param {Object} peer - The WebRTCPeer instance that will create the offer.
 */
export async function webRTCPeerOffer({ orm, peer }) {
    const offer = peer.localOffer;

    try {
        await orm.call("pos.config", "webrtc_signal", [
            odoo.pos_config_id,
            odoo.login_number,
            {
                data: offer,
                identifier: peer.identifier,
            },
        ]);
        enhancedConsole("info", "WEBRTC", `${peer.id} - Offer sent`);
    } catch {
        enhancedConsole("red", "WEBRTC", `${peer.id} - Error sending offer`);
    }
}
