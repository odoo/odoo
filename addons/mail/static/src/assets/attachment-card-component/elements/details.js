/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            details
        [Element/model]
            AttachmentCardComponent
        [web.Element/class]
            d-flex
            justify-content-center
        [web.Element/style]
            [web.scss/flex-flow]
                column
            [web.scss/min-width]
                0
                {Dev/comment}
                    This allows the text ellipsis in the flex element
            {Dev/comment}
                prevent hover delete button & attachment image to be too close to the text
            [web.scss/padding-left]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/padding-right]
                {scss/map-get}
                    {scss/$spacers}
                    1
`;
