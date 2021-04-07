odoo.define("website.tour.default_shape_gets_palette_colors", function (require) {
"use strict";

var tour = require("web_tour.tour");
const wTourUtils = require('website.tour_utils');

tour.register("default_shape_gets_palette_colors", {
    test: true,
    url: "/?enable_editor=1",
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
        trigger: '#wrap .s_text_image .o_we_shape',
        run: () => {
            const shape = $('#wrap .s_text_image .o_we_shape')[0];
            if (shape.style.backgroundImage) {
                console.error("error The default shape has a background-image in its inline style (should rely on the class)");
            }
        },
    },
]);
});
