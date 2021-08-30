/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            FollowerListMenuComponent
        [Element/onKeydown]
            {web.Event/stopPropagation}
                @ev
            {switch}
                @ev
                .{web.KeyboardEvent/key}
            .{case}
                [Escape]
                    {web.Event/preventDefault}
                        @ev
                    {FollowerListMenuComponent/_hide}
                        @record
        [web.Element/style]
            [web.scss/position]
                relative
`;
