/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            spotlightSvg
        [Element/model]
            RtcLayoutMenuComponent
        [web.Element/tag]
            svg
        [web.Element/viewBox]
            0 0 300 300
        [Element/slot]
            {html}
                <g transform="matrix(3.38 0 0 4.04 150 150)">
                    <rect style="fill: currentColor" x="-38" y="-20" rx="0" ry="0" width="75" height="39"/>
                </g>
`;
