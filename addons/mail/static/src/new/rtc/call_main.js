/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { CallActionList } from "@mail/new/rtc/call_action_list";
import { CallParticipantCard } from "@mail/new/rtc/call_participant_card";
import { isEventHandled, markEventHandled } from "@mail/new/utils/misc";

const { Component, useState, useRef, onMounted, onPatched, onWillUnmount } = owl;

export class CallMain extends Component {
    static components = { CallActionList, CallParticipantCard };
    static props = ["thread", "fullscreen", "sidebar", "visibleCards", "compact?", "minimized?"];
    static template = "mail.call_main";

    overlayTimeout;

    setup() {
        super.setup();
        this.state = useState({
            tileWidth: 0,
            tileHeight: 0,
            columnCount: 0,
            overlay: false,
        });
        this.grid = useRef("grid");
        onMounted(() => {
            this.resizeObserver = new ResizeObserver(() => this.arrangeTiles());
            this.resizeObserver.observe(this.grid.el);
            this.arrangeTiles();
        });
        onPatched(() => this.arrangeTiles());
        onWillUnmount(() => {
            this.resizeObserver.disconnect();
            browser.clearTimeout(this.overlayTimeout);
        });
    }

    get visibleCards() {
        if (this.props.thread.activeRtcSession) {
            return [{
                key: "session_" + this.props.thread.activeRtcSession.id,
                session: this.props.thread.activeRtcSession,
            }];
        }
        return this.props.visibleCards;
    }

    get hasSidebarButton() {
        return Boolean(
            this.props.thread.activeRtcSession && this.state.overlay && !this.props.compact
        );
    }

    get isControllerFloating() {
        return (
            this.props.fullscreen.isActive ||
            (this.props.thread.activeRtcSession && !this.props.compact)
        );
    }

    onMouseleave(ev) {
        if (ev.relatedTarget && ev.relatedTarget.closest(".o-mail-call-main-controls")) {
            // the overlay should not be hidden when the cursor leaves to enter the controller popover
            return;
        }
        this.state.overlay = false;
    }

    onClick() {
        this.showOverlay();
    }

    onMousemove(ev) {
        if (isEventHandled(ev, "CallMain.MousemoveOverlay")) {
            return;
        }
        this.showOverlay();
    }

    onClickHideSidebar() {
        return;
    }

    onClickShowSidebar() {
        return;
    }

    onMousemoveOverlay(ev) {
        markEventHandled(ev, "CallMain.MousemoveOverlay");
        this.state.overlay = true;
        browser.clearTimeout(this.overlayTimeout);
    }

    showOverlay() {
        this.state.overlay = true;
        browser.clearTimeout(this.overlayTimeout);
        this.overlayTimeout = browser.setTimeout(() => {
            this.state.overlay = false;
        }, 3000);
    }

    arrangeTiles() {
        if (!this.grid.el) {
            return;
        }
        const { width, height } = this.grid.el.getBoundingClientRect();
        const aspectRatio = this.props.minimized ? 1 : 16 / 9;
        const tileCount = this.grid.el.children.length;
        let optimal = {
            area: 0,
            columnCount: 0,
            tileHeight: 0,
            tileWidth: 0,
        };
        for (let columnCount = 1; columnCount <= tileCount; columnCount++) {
            const rowCount = Math.ceil(tileCount / columnCount);
            const potentialHeight = width / (columnCount * aspectRatio);
            const potentialWidth = height / rowCount;
            let tileHeight;
            let tileWidth;
            if (potentialHeight > potentialWidth) {
                tileHeight = Math.floor(potentialWidth);
                tileWidth = Math.floor(tileHeight * aspectRatio);
            } else {
                tileWidth = Math.floor(width / columnCount);
                tileHeight = Math.floor(tileWidth / aspectRatio);
            }
            const area = tileHeight * tileWidth;
            if (area <= optimal.area) {
                continue;
            }
            optimal = {
                area,
                columnCount,
                tileHeight,
                tileWidth,
            };
        }
        Object.assign(this.state, {
            tileWidth: optimal.tileWidth,
            tileHeight: optimal.tileHeight,
            columnCount: optimal.columnCount,
        });
    }
}
