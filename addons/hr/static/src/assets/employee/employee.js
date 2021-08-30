/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Employee
        [Model/fields]
            hasCheckedUser
            id
            partner
            user
        [Model/actions]
            Employee/checkIsUser
            Employee/convertData
            Employee/getChat
            Employee/openChat
            Employee/openProfile
            Employee/performRpcRead
            Employee/performRpcSearchRead
        [Model/id]
            Employee/id
`;
