// userId -> (rtc connection, data channel, isInitiator)
const peerMap = new Map();
const newConnectionEmitter = new EventTarget();

export const createWebRtcCollaboration = (configuration, myUserId) => {
    const room = 'main';

    // Signaling server
    // Connect to the signaling server
    var socket = window.io.connect();

    socket.on('joined', function ({ userId }) {
        if (userId !== myUserId) {
            const isInitiator = true;
            const newPeerConnection = createPeerConnection(isInitiator, userId, configuration);
            peerMap.set(userId, {
                isInitiator,
                ...newPeerConnection,
            });
        }
    });

    socket.on('message', function ({ to, from, message }) {
        if (to === myUserId) {
            signalingMessageCallback(from, message);
        }
    });

    // Joining a room.
    socket.emit('create or join', { room, userId: myUserId });

    /**
     * Send message to signaling server
     */
    function sendMessage(message) {
        socket.emit('message', message);
    }

    // WebRTC peer connection and data channel

    function signalingMessageCallback(from, message) {
        if (!peerMap.has(from)) {
            const isInitiator = false;
            const newPeerConnection = createPeerConnection(isInitiator, from, configuration);
            peerMap.set(from, {
                isInitiator,
                ...newPeerConnection,
            });
            const ev = new Event('newPeerConnection');
            ev.peerConnection = newPeerConnection;
            newConnectionEmitter.dispatchEvent(ev);
        }
        const { peerConn } = peerMap.get(from);
        if (message.type === 'offer') {
            return peerConn
                .setRemoteDescription(new RTCSessionDescription(message))
                .then(() => {
                    return peerConn.createAnswer(
                        desc => onLocalSessionCreated(desc, peerConn, from),
                        logError,
                    );
                })
                .catch(logError);
        } else if (message.type === 'answer') {
            return peerConn
                .setRemoteDescription(new RTCSessionDescription(message))
                .catch(logError);
        } else if (message.type === 'candidate') {
            return peerConn.addIceCandidate(
                new RTCIceCandidate({
                    candidate: message.candidate,
                    sdpMLineIndex: message.label,
                    sdpMid: message.id,
                }),
            );
        }
    }

    function createPeerConnection(isInitiator, userId, config) {
        const peerConn = new RTCPeerConnection(config);
        let dataChannel;
        // send any ice candidates to the other peer
        peerConn.addEventListener('icecandidate', function (event) {
            if (event.candidate) {
                sendMessage({
                    message: {
                        type: 'candidate',
                        label: event.candidate.sdpMLineIndex,
                        id: event.candidate.sdpMid,
                        candidate: event.candidate.candidate,
                    },
                    to: userId,
                    from: myUserId,
                });
            }
        });
        peerConn.addEventListener('datachannel', function (event) {
            const ev = new Event('newDataChannel');
            ev.connectionObject = {
                isInitiator,
                peerConn,
                dataChannel: event.channel,
            };
            newConnectionEmitter.dispatchEvent(ev);
            peerMap.set(userId, { ...peerMap.get(userId), dataChannel: event.channel });
        });
        if (isInitiator) {
            dataChannel = peerConn.createDataChannel('history');

            peerConn
                .createOffer()
                .then(function (offer) {
                    return peerConn.setLocalDescription(offer);
                })
                .then(() => {
                    sendMessage({
                        message: peerConn.localDescription,
                        to: userId,
                        from: myUserId,
                    });
                })
                .catch(logError);

            const ev = new Event('newDataChannel');
            ev.connectionObject = {
                isInitiator,
                peerConn,
                dataChannel,
            };
            newConnectionEmitter.dispatchEvent(ev);
        }
        return { peerConn, dataChannel };
    }

    function onLocalSessionCreated(desc, peerConn, userId) {
        peerConn
            .setLocalDescription(desc)
            .then(function () {
                sendMessage({ message: peerConn.localDescription, to: userId, from: myUserId });
            })
            .catch(logError);
    }

    function logError(err) {
        if (!err) return;
        if (typeof err === 'string') {
            console.warn(err);
        } else {
            console.warn(err.toString(), err);
        }
    }
    return {
        newConnectionEmitter,
        broadcast: message => {
            peerMap.forEach(({ dataChannel }) => {
                if (dataChannel && dataChannel.readyState === 'open') {
                    dataChannel.send(message);
                }
            });
        },
        peerMap,
    };
};
