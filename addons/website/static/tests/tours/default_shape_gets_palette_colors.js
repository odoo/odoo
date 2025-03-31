/** @odoo-module **/

import { queryFirst } from "@odoo/hoot-dom";
import {
    changeOption,
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("default_shape_gets_palette_colors", {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    }),
    ...clickOnSnippet({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    changeOption('ColoredLevelBackground', 'Shape'),
    {
        content: "Check that shape does not have a background-image in its inline style",
        trigger: ':iframe #wrap .s_text_image .o_we_shape',
        run() {
            const shape = queryFirst(":iframe :not(.o_ignore_in_tour) #wrap .s_text_image .o_we_shape");
            if (shape.style.backgroundImage) {
                throw new Error("The default shape has a background-image in its inline style (should rely on the class)");
            }
        },
    },
]);
