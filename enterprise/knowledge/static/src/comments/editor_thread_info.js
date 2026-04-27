export class EditorThreadInfo {
    constructor({
        beaconPair,
        threadId,
        computeTextMap = () => [],
        enableBeaconPair = () => {},
        disableBeaconPair = () => {},
        isOwned = () => {},
        removeBeaconPair = () => {},
        setSelectionInBeaconPair = () => {},
        setBeaconPairId = () => {},
    } = {}) {
        this.beaconPair = beaconPair;
        this.threadId = threadId;
        this.computeTextMap = computeTextMap;
        this.isOwned = isOwned;
        this.removeBeaconPair = removeBeaconPair;
        this.setSelectionInBeaconPair = setSelectionInBeaconPair;
        this.setBeaconPairId = setBeaconPairId;
        this.enableBeaconPair = enableBeaconPair;
        this.disableBeaconPair = disableBeaconPair;
        this.onActivateMap = new Map();
        this.onFocusMap = new Map();
        this.hover = false;
        this.top = 0;
        this.anchorText = this.computeCurrentAnchorText();
    }

    computeCurrentAnchorText() {
        return this.computeTextMap(this.beaconPair).join("\n").trim();
    }

    setThreadId(id) {
        this.threadId = id;
        this.setBeaconPairId(this.beaconPair, id);
    }

    enableBeacons() {
        this.enableBeaconPair(this.beaconPair);
    }

    disableBeacons() {
        this.disableBeaconPair(this.beaconPair);
    }

    removeBeacons() {
        this.removeBeaconPair(this.beaconPair);
    }

    select() {
        this.setSelectionInBeaconPair(this.beaconPair);
    }

    handleEventMapEntries(ev, map) {
        map.get("main")?.(ev);
        for (const [key, handler] of map.entries()) {
            if (key.isConnected) {
                handler(ev);
            } else if (key !== "main") {
                map.delete(key);
            }
        }
    }

    isProtected() {
        return !this.isOwned(this.beaconPair);
    }

    onActivate(ev) {
        this.handleEventMapEntries(ev, this.onActivateMap);
    }

    onFocus(ev) {
        this.handleEventMapEntries(ev, this.onFocusMap);
    }
}
