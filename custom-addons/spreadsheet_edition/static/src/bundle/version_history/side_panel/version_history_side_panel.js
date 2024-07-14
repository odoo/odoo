/** @odoo-module */

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { VersionHistoryItem } from "./version_history_item";

export class VersionHistorySidePanel extends Component {
    revNbr = 50;

    setup() {
        this.containerRef = useRef("container");
        this.state = useState({
            currentRevisionId: this.revisions[0]?.nextRevisionId,
            isEditingName: false,
            loaded: this.revNbr,
        });

        onMounted(() => {
            this.focus();
        });
    }

    get revisions() {
        return this.env.historyManager.getRevisions();
    }

    get loadedRevisions() {
        return this.revisions.slice(0, this.state.loaded);
    }

    focus() {
        this.containerRef.el?.focus();
    }

    onRevisionClick(revisionId) {
        this.env.model.dispatch("GO_TO_REVISION", { revisionId });
        this.state.currentRevisionId = revisionId;
    }

    onLoadMoreClicked() {
        this.state.loaded = Math.min(this.state.loaded + this.revNbr, this.revisions.length);
    }

    onKeyDown(ev) {
        let increment = 0;
        switch (ev.key) {
            case "ArrowUp":
                increment = -1;
                ev.preventDefault();
                break;
            case "ArrowDown":
                increment = 1;
                ev.preventDefault();
                break;
        }
        if (increment) {
            const revisions = this.loadedRevisions;
            const currentIndex = revisions.findIndex(
                (r) => r.nextRevisionId === this.state.currentRevisionId
            );
            const nextIndex = Math.max(0, Math.min(revisions.length - 1, currentIndex + increment));
            this.state.currentRevisionId = revisions[nextIndex].nextRevisionId;
            this.env.model.dispatch("GO_TO_REVISION", {
                revisionId: this.state.currentRevisionId,
            });
        }
    }
}

VersionHistorySidePanel.template = "spreadsheet_edition.VersionHistory";
VersionHistorySidePanel.props = { onCloseSidePanel: Function };
VersionHistorySidePanel.components = {
    VersionHistoryItem,
};
