/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            name
        [Element/model]
            NotificationRequestComponent
        [web.Element/tag]
            span
        [Record/models]
            NotificationListItemComponent/bold
            NotificationListItemComponent/name
        [web.Element/textContent]
            {String/sprintf}
                [0]
                    {Locale/text}
                        %s has a request
                [1]
                    {Env/partnerRoot}
                    .{Partner/nameOrDisplayName}
`;
