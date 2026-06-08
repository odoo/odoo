import { CALL_GRID_LAYOUT } from "@mail/discuss/call/common/call_layout";

import { Component, props, t } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/** @typedef {import("@mail/discuss/call/common/call_layout").CallLayout} CallLayout */

/**
 * @typedef {Object} LayoutOption
 * @property {CallLayout} value layout identifier.
 * @property {string} label translated display name.
 */

/**
 * "Change layout" dialog letting the user pick the meeting grid layout, cap the number of tiles
 * and hide tiles without video. The grid layout and tile cap are persisted in user settings.
 *
 * @extends {Component<{ channel: import("models").DiscussChannel, close?: () => void }, Env>}
 */
export class ChangeLayoutDialog extends Component {
    static components = { Dialog };
    static template = "discuss.ChangeLayoutDialog";

    setup() {
        super.setup();
        this.CALL_GRID_LAYOUT = CALL_GRID_LAYOUT;
        this.store = useService("mail.store");
        this.props = props({
            channel: t.instanceOf(this.store["discuss.channel"].Class),
            close: t.function([]).optional(),
        });
        this.rtc = useService("discuss.rtc");
    }

    /** @returns {LayoutOption[]} selectable layout options, in display order. */
    get layoutOptions() {
        return [
            { value: CALL_GRID_LAYOUT.AUTO, label: _t("Auto (dynamic)") + " ✨" },
            { value: CALL_GRID_LAYOUT.TILED, label: _t("Tiled") },
            { value: CALL_GRID_LAYOUT.SPOTLIGHT, label: _t("Spotlight") },
            { value: CALL_GRID_LAYOUT.SIDEBAR, label: _t("Sidebar") },
            { value: CALL_GRID_LAYOUT.DISCUSS, label: _t("Discuss") },
        ];
    }

    /**
     * Outside the fullscreen meeting view the call is shown in the windowed Discuss app, so the
     * "Discuss" row is the active one; the persisted grid layout only applies in fullscreen.
     *
     * @param {LayoutOption["value"]} value layout the row represents.
     * @returns {boolean} whether the row is the currently active layout.
     */
    isSelected(value) {
        if (!this.rtc.isFullscreen) {
            return value === CALL_GRID_LAYOUT.DISCUSS;
        }
        return this.store.settings.callLayout === value;
    }

    /**
     * @param {LayoutOption["value"]} value chosen layout; "discuss" exits the meeting view instead
     *  of being persisted, pointing the Discuss app at the meeting channel so it is shown instead of
     *  the last visited thread. Picking any grid layout from the windowed Discuss view persists it
     *  and opens the full-window meeting view (browser UI kept; only the fullscreen button hides it).
     * @returns {void}
     */
    onSelectLayout(value) {
        if (value === CALL_GRID_LAYOUT.DISCUSS) {
            this.rtc.exitFullscreen();
            if (this.store.discuss.isActive) {
                this.props.channel.setAsDiscussThread();
            }
            this.props.close?.();
            return;
        }
        this.store.settings.callLayout = value;
        if (!this.rtc.isFullscreen) {
            this.rtc.enterFullscreen();
            this.props.close?.();
        }
    }
}
