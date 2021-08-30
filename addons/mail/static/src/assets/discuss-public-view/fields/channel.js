/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the channel linked to this discuss public view.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            channel
        [Field/model]
            DiscussPublicView
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
`;
