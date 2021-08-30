/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcCallViewerComponent
        [Model/fields]
            columnCount
            rtcCallViewer
            tileHeight
            tileWidth
        [Model/template]
            root
                participantContainer
                    mainParticipantContainer
                        mainParticipantCard
                    grid
                        gridTileForeach
                controls
                    controlsOverlayContainer
                        rtcController
                settings
                    settingsContent
                changeLayout
                    changeLayoutContent
        [Model/actions]
            RtcCallViewerComponent/_computeTessellation
            RtcCallViewerComponent/_setTileLayout
        [Model/lifecycles]
            onUpdate
`;
