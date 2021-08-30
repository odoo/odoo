/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            NotificationRequestComponent
        [Model/fields]
            view
        [Model/template]
            root
                sidebar
                    imageContainer
                        image
                        partnerImStatusIcon
                content
                    header
                        name
                    core
                        inlineText
        [Model/actions]
            NotificationRequestComponent/_handleResponseNotificationPermission
`;
