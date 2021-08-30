/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            body
        [Element/model]
            FollowerSubtypeListComponent
        [web.Element/tag]
            main
        [web.Element/class]
            modal-body
`;
