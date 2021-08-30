/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            RtcLayoutMenuComponent
        [Model/fields]
            layoutMenu
        [Model/template]
            root
                showAll
                    showAllInputContainer
                        showAllInput
                        showAllText
                showOnlyVideo
                    showOnlyVideoInputContainer
                        showOnlyVideoInput
                        showOnlyVideoText
                separator
                tiled
                    tiledInputContainer
                        tiledInput
                        tiledText
                        tiledIcon
                            tiledSvg
                spotlight
                    spotlightInputContainer
                        spotlightInput
                        spotlightText
                        spotlightIcon
                            spotlightSvg
                sidebar
                    sidebarInputContainer
                        sidebarInput
                        sidebarText
                        sidebarIcon
                            sidebarSvg
`;
