// Time to consider a user offline in ms. This fixes the problem of the
// navigator closing rtc connection when the mac laptop screen is closed.
const CONSIDER_OFFLINE_TIME = 1000;
// Check wether the computer could be offline. This fixes the problem of the
// navigator closing rtc connection when the mac laptop screen is closed.
// This case happens on Mac OS on every browser when the user close it's laptop
// screen. At first, the os/navigator closes all rtc connection, and after some
// times, the os/navigator internet goes offline without triggering an
// offline/online event.
// However, if the laptop screen is open and the connection is properly remove
// (e.g. disconnect wifi), the event is properly triggered.
const CHECK_OFFLINE_TIME = 1000;
const PTP_PEER_DISCONNECTED_STATES = ["failed", "closed", "disconnected"];

export class OfflineDetection {
    constructor(options) {
        this.ptp = options.ptp;
        this.onReconnect = options.onReconnect;

        this.checkConnectionChange = () => {
            if (!navigator.onLine) {
                this.signalOffline();
            } else {
                this.signalOnline();
            }
        };

        window.addEventListener("online", this.checkConnectionChange);
        window.addEventListener("offline", this.checkConnectionChange);

        this.collaborationInterval = setInterval(async () => {
            if (this.offlineTimeout) {
                return;
            }
            const peersInfos = Object.values(this.ptp.peersInfos);
            const couldBeDisconnected =
                Boolean(peersInfos.length) &&
                peersInfos.every((x) =>
                    PTP_PEER_DISCONNECTED_STATES.includes(
                        x.peerConnection && x.peerConnection.connectionState
                    )
                );
            if (couldBeDisconnected) {
                this.offlineTimeout = setTimeout(() => {
                    this.signalOffline();
                }, CONSIDER_OFFLINE_TIME);
            }
        }, CHECK_OFFLINE_TIME);
    }
    stop() {
        clearInterval(this.collaborationInterval);
    }

    signalOffline() {
        this.isOnline = false;
    }
    async signalOnline() {
        clearTimeout(this.offlineTimeout);
        this.offlineTimeout = undefined;

        if (this.isOnline || !navigator.onLine) {
            return;
        }
        this.isOnline = true;
        if (!this.ptp) {
            return;
        }

        this.onReconnect();
    }
}
