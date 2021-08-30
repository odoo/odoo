/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Boolean that determines if there is a pending open state change,
        which is requested by the client but not yet confirmed by the server.

        This field can be updated to immediately change the open state on the
        interface and to notify the server of the new state.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isPendingOpen
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
