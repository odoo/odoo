/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

import Dialog from 'web.OwlDialog';

const { Component, useState } = owl;
const { useRef } = owl.hooks;

const components = {
    Dialog,
};

// TODO a nice-to-have would be a resize handle under the videos.

export class RtcCallViewer extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            tileWidth: 0,
            tileHeight: 0,
            columnCount: 0,
        });
        this.tileContainerRef = useRef('tileContainer');
        useUpdate({ func: () => this._update() });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.rtcCallViewer && this.rtcCallViewer.threadView.thread;
    }

    /**
     * @returns {mail.rtc_call_viewer}
     */
    get rtcCallViewer() {
        return this.messaging.models['mail.rtc_call_viewer'].get(this.props.localId);
    }

    /**
     * @returns {mail.user_setting}
     */
    get userSetting() {
        return this.messaging && this.messaging.userSetting;
    }

    /**
     * Used to make the component depend on the window size and trigger an
     * update when the window size changes.
     *
     * @returns {Object|undefined}
     */
    get windowSize() {
        const device = this.messaging && this.messaging.device;
        return device && {
            innerHeight: device.globalWindowInnerHeight,
            innerWidth: device.globalWindowInnerWidth,
        };
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _computeOptimalLayout({ containerWidth, containerHeight }) {
        let optimalLayout = {
            area: 0,
            cols: 0,
            width: 0,
            height: 0,
        };

        // finding out how many tiles are part of the dynamic grid.
        const tileCount = this.rtcCallViewer.filterVideoGrid
            ? this.thread.videoCount
            : this.thread.rtcSessions.length;

        for (let columnCount = 1; columnCount <= tileCount; columnCount++) {
            const rowCount = Math.ceil(tileCount / columnCount);
            const tileHeight = containerWidth / (columnCount * this.rtcCallViewer.aspectRatio);
            const tileWidth = containerHeight / rowCount;
            let width;
            let height;
            if (tileHeight > tileWidth) {
                height = Math.floor(containerHeight / rowCount);
                width = Math.floor(height * this.rtcCallViewer.aspectRatio);
            } else {
                width = Math.floor(containerWidth / columnCount);
                height = Math.floor(width / this.rtcCallViewer.aspectRatio);
            }
            const area = height * width;
            if (area <= optimalLayout.area) {
                continue;
            }
            optimalLayout = {
                area,
                width,
                height,
                columnCount
            };
        }
        return optimalLayout;
    }

    /**
     * @private
     */
    _setTileLayout() {
        if (!this.thread) {
            return;
        }
        if (!this.el) {
            return;
        }
        if (!this.tileContainerRef.el) {
            return;
        }
        const roomRect = this.tileContainerRef.el.getBoundingClientRect();

        const { width, height, columnCount } = this._computeOptimalLayout({
            containerWidth: roomRect.width,
            containerHeight: roomRect.height,
        });

        this.state.tileWidth = width;
        this.state.tileHeight = height;
        this.state.columnCount = columnCount;
    }

    /**
     * @private
     */
    _update() {
        this._setTileLayout();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        this.rtcCallViewer && this.rtcCallViewer.onClick();
    }

    /**
     * @private
     */
    _onLayoutSettingsDialogClosed() {
        this.messaging.userSetting.toggleLayoutSettingsWindow();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMouseMove(ev) {
        if (isEventHandled(ev, 'RtcCallViewer.MouseMoveOverlay')) {
            return;
        }
        this.rtcCallViewer && this.rtcCallViewer.onMouseMove();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onMouseMoveOverlay(ev) {
        markEventHandled(ev, 'RtcCallViewer.MouseMoveOverlay');
        this.rtcCallViewer && this.rtcCallViewer.onMouseMoveOverlay();
    }

    /**
     * @private
     */
    _onRtcSettingsDialogClosed() {
        this.messaging.userSetting.rtcConfigurationMenu.toggle();
    }

}

Object.assign(RtcCallViewer, {
    components,
    props: {
        localId: String,
    },
    template: 'mail.RtcCallViewer',
});

registerMessagingComponent(RtcCallViewer);
