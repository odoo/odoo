/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _chatterId
        [Field/model]
            ChatterContainerComponent
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/default]
            {ChatterContainerComponent/getChatterNextTemporaryId}
`;
