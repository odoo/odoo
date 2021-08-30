/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            RtcVideoComponent
        [web.Element/tag]
            video
        [Element/onLoadedmeta]
            {try}
                @ev
                .{web.Event/target}
                .{Dict/get}
                    play
                .{Function/call}
            .{catch}
                {Record/insert}
                    [Record/models]
                        Function
                    [Function/in]
                        error
                    [Function/out]
                        {if}
                            @error
                            .{typeof}
                            .{=}
                                object
                            .{&}
                                @error
                                .{Error/name}
                                .{=}
                                    NotAllowedError
                        .{then}
                            {Dev/comment}
                                Ignored as some browsers may reject play() calls
                                that do not originate from a user input.
                            {break}
                        {Error/raise}
                            @error
        [web.Element/playsinline]
            true
        [web.Element/autoplay]
            true
        [web.Element/muted]
            true
        [web.Element/style]
            [web.scss/width]
                100%
            [web.scss/height]
                100%
            [web.scss/background-color]
                black
            [web.scss/border-radius]
                {scss/$o-mail-rounded-rectangle-border-radius-sm}
            [web.scss/cursor]
                pointer
`;
