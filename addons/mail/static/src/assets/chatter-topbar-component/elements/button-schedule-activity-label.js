/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonScheduleActivityLabel
        [Element/model]
            ChatterTopbarComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            {Locale/text}
                Schedule activity
`;
