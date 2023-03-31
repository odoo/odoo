/** @odoo-module **/

import core from "web.core";
var QWeb = core.qweb;
import Fullscreen from "@website_slides/js/slides_course_fullscreen_player";

Fullscreen.include({
    /**
     * Extend the _renderSlide method so that slides of category "certification"
     * are also taken into account and rendered correctly
     *
     * @private
     * @override
     */
    _renderSlide: function (){
        var def = this._super.apply(this, arguments);
        var $content = this.$('.o_wslides_fs_content');
        if (this.get('slide').category === "certification"){
            $content.html(QWeb.render('website.slides.fullscreen.certification',{widget: this}));
        }
        return Promise.all([def]);
    },
});
