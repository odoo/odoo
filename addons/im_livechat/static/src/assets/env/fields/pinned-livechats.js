/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        All pinned livechats that are known.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            pinnedLivechats
        [Field/model]
            MobileMessagingNavbarView
        [Field/feature]
            im_livechat
        [Field/type]
            many
        [Field/target]
            Thread
        [Field/isReadonly]
            true
        [Field/inverse]
            Thread/messagingAsPinnedLivechat
`;
