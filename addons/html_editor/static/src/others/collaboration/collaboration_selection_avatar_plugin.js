import { Plugin } from "@html_editor/plugin";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

/**
 * @typedef {Object} SelectionInfo
 * @property {import("@html_editor/core/history_plugin").SerializedSelection} selection
 * @property {string} color
 * @property {string} peerId
 * @property {string} peerName
 * @property {string} avatarPositionKey
 * @property {HTMLElement} avatarElement
 * @property {HTMLElement} avatarTargetElement
 */

export const AVATAR_SIZE = 25;

export class CollaborationSelectionAvatarPlugin extends Plugin {
    static id = "collaborationSelectionAvatar";
    static dependencies = ["history", "position", "localOverlay", "collaborationOdoo"];
    resources = {
        /** Handlers */
        collaboration_notification_handlers: this.handleCollaborationNotification.bind(this),
        external_history_step_handlers: this.refreshSelection.bind(this),
        layout_geometry_change_handlers: this.refreshSelection.bind(this),
        set_movable_element_handlers: this.disableAvatarForElement.bind(this),
        unset_movable_element_handlers: this.enableAvatars.bind(this),
        collaborative_selection_update_handlers: this.updateSelection.bind(this),

        collaboration_peer_metadata_providers: () => ({ avatarUrl: this.avatarUrl }),
    };

    /** @type {Map<string, SelectionInfo>} */
    selectionInfos = new Map();

    setup() {
        this.avatarOverlay = this.dependencies.localOverlay.makeLocalOverlay("oe-avatars-overlay");
        this.avatarsCountersOverlay = this.dependencies.localOverlay.makeLocalOverlay(
            "oe-avatars-counters-overlay"
        );
        this.avatarUrl = `${
            browser.location.origin
        }/web/image?model=res.users&field=avatar_128&id=${encodeURIComponent(user.userId)}`;
    }
    handleCollaborationNotification({ notificationName, notificationPayload }) {
        switch (notificationName) {
            case "ptp_remove":
                this.selectionInfos.delete(notificationPayload);
                this.refreshSelection();
        }
    }

    /**
     * @param {import("./collaboration_odoo_plugin").CollaborationSelection} selection
     */
    updateSelection(selection) {
        /** @type {SelectionInfo} */
        const savedSelection = this.selectionInfos.get(selection.peerId) || {};
        const newSelection = Object.assign(savedSelection, selection);
        this.selectionInfos.set(selection.peerId, newSelection);
        this.drawPeerAvatar(newSelection);
        this.updateAvatarCounters();
    }
    /**
     * @param {SelectionInfo} selectionInfo
     */
    drawPeerAvatar(selectionInfo) {
        const { selection, peerId } = selectionInfo;
        const peerMetadata = this.dependencies.collaborationOdoo.getPeerMetadata(peerId);
        if (!peerMetadata) {
            return;
        }
        const { avatarUrl, peerName = _t("Anonymous") } = peerMetadata;
        const anchorNode = this.dependencies.history.getNodeById(selection.anchorNodeId);
        const focusNode = this.dependencies.history.getNodeById(selection.focusNodeId);
        if (!anchorNode || !focusNode || !anchorNode.isConnected || !focusNode.isConnected) {
            return;
        }
        const anchorBlock =
            closestElement(anchorNode, (el) => isBlock(el) && el.parentElement === this.editable) ||
            closestBlock(anchorNode);
        if (!anchorBlock) {
            return;
        }

        const containerRect = this.avatarOverlay.getBoundingClientRect();

        // Draw user avatar.
        let avatarElement = selectionInfo.avatarElement;
        if (!avatarElement) {
            avatarElement = this.document.createElement("div");
            avatarElement.className = "oe-collaboration-caret-avatar";
            avatarElement.style.display = "none";
            const image = this.document.createElement("img");
            avatarElement.append(image);
            image.onload = () => avatarElement.style.removeProperty("display");
            image.setAttribute("src", avatarUrl);
            image.classList.add("object-fit-cover");
        }
        // Avoid re-appending the element in the dom.
        if (!avatarElement.parentElement) {
            this.avatarOverlay.append(avatarElement);
        }
        // Make sure data is up to date.
        selectionInfo.avatarElement = avatarElement;
        selectionInfo.peerName = peerName;
        selectionInfo.avatarTargetElement = anchorBlock;
        this.selectionInfos.set(peerId, selectionInfo);

        const anchorBlockRect = anchorBlock.getBoundingClientRect();
        const top = anchorBlockRect.y - containerRect.y;
        avatarElement.style.top = top + "px";
        const closestList = closestElement(anchorNode, "ul, ol"); // Prevent overlap bullets.
        const anchorX = closestList ? closestList.getBoundingClientRect().x : anchorBlockRect.x;
        const left = anchorX - containerRect.x - AVATAR_SIZE;
        avatarElement.style.left = left + "px";
        selectionInfo.avatarPositionKey = `${left}|${top}`;
    }
    updateAvatarCounters() {
        const avatarsOverlaps = {};
        for (const info of this.selectionInfos.values()) {
            const key = info.avatarPositionKey;
            avatarsOverlaps[key] = avatarsOverlaps[key] || new Set();
            avatarsOverlaps[key].add(info);
        }

        // Render avatars overlap.
        this.avatarsCountersOverlay.replaceChildren();
        for (const [overlapKey, infos] of Object.entries(avatarsOverlaps)) {
            const size = infos.size;
            if (size > 1) {
                const [left, top] = overlapKey.split("|").map((n) => parseInt(n, 10));
                const div = document.createElement("div");
                div.className = "oe-overlapping-counter";
                div.style.left = left + 10 + "px";
                div.style.top = top + 10 + "px";
                div.innerText = size;
                this.avatarsCountersOverlay.append(div);
            }
        }
    }
    refreshSelection() {
        if (!this.selectionInfos.size) {
            this.avatarOverlay.replaceChildren();
        }
        this.avatarsCountersOverlay.replaceChildren();
        for (const selection of this.selectionInfos.values()) {
            this.drawPeerAvatar(selection);
        }
        this.updateAvatarCounters();
    }

    disableAvatarForElement(element) {
        this.enableAvatars();
        for (const info of this.selectionInfos.values()) {
            if (info.avatarTargetElement === element) {
                if (!info.avatarElement.classList.contains("invisible")) {
                    info.avatarElement.classList.add("invisible");
                }
            }
        }
    }
    enableAvatars() {
        for (const element of this.avatarOverlay.querySelectorAll(
            ".oe-collaboration-caret-avatar.invisible"
        )) {
            element.classList.remove("invisible");
        }
    }
}
