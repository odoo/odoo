/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The menu_id of discuss app, received on mail/init_messaging and
        used to open discuss from elsewhere.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            menuId
        [Field/model]
            Discuss
        [Field/type]
            attr
        [Field/default]
            null
`;
