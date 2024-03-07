/** @odoo-module **/

import { queryFirst } from "@odoo/hoot-dom";
import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour("default_shape_gets_palette_colors", {
    test: true,
    url: '/',
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    wTourUtils.clickOnSnippet({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    wTourUtils.changeOption('ColoredLevelBackground', 'Shape'),
    {
        content: "Check that shape does not have a background-image in its inline style",
        trigger: ':iframe #wrap .s_text_image .o_we_shape',
        run: () => {
            const shape = queryFirst(":iframe :not(.o_ignore_in_tour) #wrap .s_text_image .o_we_shape");
            if (shape.style.backgroundImage) {
                console.error("error The default shape has a background-image in its inline style (should rely on the class)");
            }
        },
    },
]);
