/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Definition
        [Model/fields]
            chunks
            id
        [Model/id]
            Definition/id
`;
