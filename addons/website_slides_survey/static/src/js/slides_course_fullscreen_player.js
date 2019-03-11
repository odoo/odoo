odoo.define('website_slides_survey.fullscreen', function (require) {
    "use strict";

    var core = require('web.core');
    var QWeb = core.qweb;
    var Fullscreen = require('website_slides.fullscreen');

    Fullscreen.include({
        xmlDependencies: (Fullscreen.prototype.xmlDependencies || []).concat(
            ["/website_slides_survey/static/src/xml/website_slides_fullscreen.xml"]
        ),
        _fetchCertificationUrl: function (){
            var slide = this.get("slide");
            var self = this;
            return this._rpc({
                route: "/slides_survey/certification_url/get",
                params: {
                    slide_id: slide.id
                }
            }).then(function (data){
                if (data){
                    slide.certificationUrl = data.certification_url;
                    self.set('slide', slide);
                }
            });
        },
        /**
         * Extend the render method so that slides of type "certification"
         * are rendered correctly
         *
         * @override
         */
        _renderSlide: function (){
            this._super.apply(this, arguments);
            var slide = this.get('slide');
            var $content = this.$('.o_wslides_fs_content');
            if (slide.type === "certification"){
                if (slide.certificationUrl){
                    $content.html(QWeb.render('website.slides.fullscreen.certification',{slide: slide}));
                } else {
                    this._fetchCertificationUrl().then(function (){
                        $content.html(QWeb.render('website.slides.fullscreen.certification',{slide: slide}));
                    });
                }
            }
            return $.when();
        },
    });
});
