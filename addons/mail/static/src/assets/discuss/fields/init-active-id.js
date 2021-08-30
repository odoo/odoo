/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Formatted init thread on opening discuss for the first time,
        when no active thread is defined. Useful to set a thread to
        open without knowing its local id in advance.
        Support two formats:
           {string} <threadModel>_<threadId>
           {int} <channelId> with default model of 'mail.channel'
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            initActiveId
        [Field/model]
            Discuss
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            mail.box_inbox
`;
