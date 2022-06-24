odoo.define("website.tour.default_shape_gets_palette_colors", function (require) {
"use strict";

var tour = require("web_tour.tour");
const wTourUtils = require('website.tour_utils');

tour.register("default_shape_gets_palette_colors", {
    test: true,
    url: wTourUtils.getClientActionUrl('/', true),
}, [
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
        trigger: 'iframe #wrap .s_text_image .o_we_shape',
        run: () => {
            const shape = $('iframe:not(.o_ignore_in_tour)').contents().find('#wrap .s_text_image .o_we_shape')[0];
            if (shape.style.backgroundImage) {
                console.error("error The default shape has a background-image in its inline style (should rely on the class)");
            }
        },
    },
]);
});
