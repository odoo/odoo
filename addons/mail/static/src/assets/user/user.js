/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            User
        [Model/fields]
            displayName
            id
            isInternalUser
            model
            nameOrDisplayName
            partner
            resUsersSettingsId
        [Model/id]
            USer/id
        [Model/actions]
            User/convertData
            User/fetchPartner
            User/getChat
            User/openChat
            User/openProfile
            User/performRpcRead
`;
