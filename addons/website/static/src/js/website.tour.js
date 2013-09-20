
(function() {
    var website = openerp.website;
    website.Tour = openerp.Class.extend({
        template: 'website.tour',
        init: function () {
            this.template = "<div class='popover tour'> \
             <div class='arrow'></div> \
             <h3 class='popover-title'></h3> \
             <div class='popover-content'></div>\
             <nav class='popover-navigation'>\
                <div class='btn-group'>\
                    <button class='btn btn-default' data-role='next'>Continue »</button>\
                </div>\
                <button class='btn btn-default' data-role='end'>Close Tutorial</button> \
            </nav> \
            </div>"
            
        },
        start: function(){
            this.tour = new this.init_plugin();
            this.add_step();
            this.tour.restart(true);
        },
        add_step: function(){
            this.tour.addSteps([
                {
                    element: "header",
                    placement: "bottom",
                    title: "Welcome to your website!",
                    content: "This tutorial will guide you through the firsts steps to build your enterprise class website.",
                },{
                    element: '.navbar-header:first',
                    placement: "bottom",
                    title: "Edit this page",
                    content: "Every page of your website can be edited. Click the <button type='button' data-action='edit' class='btn btn-primary'>Edit</button> button to modify your homepage.",
                }
            ]);
        },
        init_plugin: function(){
            return new Tour({
                name: "tour",
                container: "body",
                keyboard: true,
                storage: window.localStorage,
                debug: true,
                backdrop: false,
                redirect: true,
                orphan: true,
                basePath: "",
                template: this.template,
                afterGetState: function(key, value) {},
                afterSetState: function(key, value) {},
                afterRemoveState: function(key, value) {},
                onStart: function(tour) {},
                onEnd: function(tour) {},
                onShow: function(tour) {},
                onShown: function(tour) {},
                onHide: function(tour) {},
                onHidden: function(tour) {},
                onNext: function(tour){},
                onPrev: function(tour) {}
            });
        }
        
    });
    $(document).ready(function () {
        if (window.location.href.indexOf("?tutorial=true") != -1) {
            var Tour = new website.Tour().start()
        }
    });
}).call(this);