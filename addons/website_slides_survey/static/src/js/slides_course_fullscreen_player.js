odoo.define('website_slides_survey.fullscreen', function (require) {
"use strict";

var core = require('web.core');
var QWeb = core.qweb;
var Fullscreen = require('website_slides.fullscreen');

Fullscreen.include({
    xmlDependencies: (Fullscreen.prototype.xmlDependencies || []).concat(
        ["/website_slides_survey/static/src/xml/website_slides_fullscreen.xml"]
    ),
    _preprocessSlideData: function (slidesDataList){
        slidesDataList = this._super.apply(this, arguments);
        slidesDataList.forEach(function (slideData, index){
            if (slideData.type === "certification"){
                slideData.certificationUrl = '/slides_survey/slide/get_certification_url?slide_id=' + slideData.id;
            }
        });
        return slidesDataList;
    },
    /**
     * Extend the _renderSlide method so that slides of type "certification"
     * are also taken into account and rendered correctly
     *
     * @private
     * @override
     */
    _renderSlide: function (){
        var def = this._super.apply(this, arguments);
        var $content = this.$('.o_wslides_fs_content');
        if (this.get('slide').type === "certification"){
            $content.html(QWeb.render('website.slides.fullscreen.certification',{widget: this}));
        }
        return $.when(def);
    },
});
});


