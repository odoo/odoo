/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            emptyTitle
        [Element/model]
            MessageListComponent
        [web.Element/style]
            [web.scss/font-weight]
                bold
            [web.scss/font-size]
                1.3rem
            {web.scss/selector}
                [0]
                    &.o-neutral-face-icon:before
                [1]
                    {web.scss/extend}
                        %o-nocontent-init-image
                    {web.scss/include}
                        {scss/size}
                            120px
                            140px
                    [web.scss/background]
                        transparent
                        {scss/url}
                            /web/static/img/neutral_face.svg
                        no-repeat
                        center
`;
