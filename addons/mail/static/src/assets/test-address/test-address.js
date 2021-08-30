/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            TestAddress
        [Model/fields]
            addressInfo
            contact
            id
        [Model/id]
            TestAddress/id
`;
