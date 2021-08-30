/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ChatterComponent
        [Model/fields]
            chatter
        [Model/template]
            root
                fixedPanel
                    topbar
                    composer
                scrollPanel
                    attachmentBox
                    activityBox
                    thread
        [Model/actions]
            ChatterComponent/_notifyRendered
            ChatterComponent/getScrollableElement
        [Model/lifecycles]
            onUpdate
`;
