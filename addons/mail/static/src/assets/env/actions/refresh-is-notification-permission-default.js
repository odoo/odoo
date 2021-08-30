/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Refreshes the value of 'isNotificationPermissionDefault'.

        Must be called in flux-specific way because the browser does not
        provide an API to detect when this value changes.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Env/refreshIsNotificationPermissionDefault
        [Action/behavior]
            {Record/update}
                [0]
                    @env
                [1]
                    [Env/isNotificationPermissionDefault]
                        @env
                        .{Env/_computeIsNotificationPermissionDefault}
`;
