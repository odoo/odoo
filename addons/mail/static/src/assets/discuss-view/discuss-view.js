/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            DiscussView
        [Model/fields]
            discuss
        [Model/id]
            DiscussView/discuss
`;
