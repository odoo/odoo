/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Visitor
        [Model/fields]
            avatarUrl
            country
            displayName
            history
            id
            isConnected
            langName
            nameOrDisplayName
            partner
            threads
            websiteName
        [Model/id]
            Visitor/id
        [Model/actions]
            Visitor/convertData
`;
