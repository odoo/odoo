/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the specific name of this partner in the context of livechat.
        Either a string or undefined.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            livechatUsername
        [Field/model]
            Partner
        [Field/feature]
            im_livechat
        [Field/type]
            attr
        [Field/target]
            String
`;
