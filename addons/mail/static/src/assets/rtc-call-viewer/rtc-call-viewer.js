/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcCallViewer
        [Model/fields]
            aspectRatio
            device
            filterVideoGrid
            isControllerFloating
            isFullScreen
            isMinimized
            layout
            layoutSettingsTitle
            mainParticipantCard
            rtcController
            rtcLayoutMenu
            settingsTitle
            showOverlay
            showOverlayTimeout
            threadView
            tileParticipantCards
        [Model/id]
            RtcCallViewer/threadView
        [Model/action]
            RtcCallViewer/_onFullScreenChange
            RtcCallViewer/_onShowOverlayTimeout
            RtcCallViewer/_showOverlay
            RtcCallViewer/activateFullScreen
            RtcCallViewer/deactivateFullScreen
            RtcCallViewer/onClick
            RtcCallViewer/onLayoutSettingsDialogClosed
            RtcCallViewer/onMousemove
            RtcCallViewer/onMousemoveOverlay
            RtcCallViewer/onRtcSettingsDialogClosed
            RtcCallViewer/toggleLayoutMenu
        [Model/onChanges]
            RtcCallViewer/_onChangeRtcChannel
            RtcCallViewer/_onChangeVideoCount
`;
