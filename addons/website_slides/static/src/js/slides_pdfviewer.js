/*global $, openerp, _, PDFJS */
(function () {
    "use strict";
    var website = openerp.website;
    website.slide = website.slide || {};
    website.slide.template = website.add_template_file('/website_slides/static/src/xml/website_slides.xml');

    website.slide.PDFViewer_Launcher = function ($PDFViewer) {
        website.slide.template.then(function () {
            var slide_id = $PDFViewer.attr('slide-id'),
                file = '/slides/slide/' + slide_id + '/pdf_content',
                downloadable = $PDFViewer.attr('downloadable');
            if (slide_id) {
                var PDFViewer = new website.slide.PDFViewer(slide_id, file, downloadable);
                PDFViewer.replace($PDFViewer);
                website.slide.PDFViewer_inst = PDFViewer;
            }
        });
    };

    website.slide.PDFViewer = openerp.Widget.extend({
        template: 'website.slide.PDFViewer',
        events: {
            'click #next': 'next',
            'click #previous': 'previous',
            'click #last': 'last',
            'click #first': 'first',
            'click #fullscreen': 'fullscreen',
            'change #page_number': 'change_page_number'
        },
        init: function (id, file, downloadable) {
            this.id = id;
            this.file = file;
            this.downloadable = downloadable;
            this.file_content = null;
            this.scale = 1.5;
            this.page_number = 1;
            this.rendering = false;
            this.loaded = false;
        },
        start: function () {
            this.canvas = this.$('canvas')[0];
            this.ctx = this.canvas.getContext('2d');
            this.load_file();
        },
        load_file: function () {
            var self = this;
            PDFJS.getDocument(this.file).then(function (file_content) {
                self.file_content = file_content;
                self.page_count = file_content.numPages;
                self.loaded = true;
                self.$('#PDFLoading, #PDFLoader').hide();
                self.$('#PDFViewer').show();
                self.$('#page_count').text(self.page_count);
                self.render_page();
            });
        },
        is_loaded: function () {
            if (!this.loaded) {
                this.$('#PDFLoading').show();
                this.$('#PDFViewer-image').css({'opacity': 0.2});
                return false;
            }
            return true;
        },
        render_page: function (page_number) {
            var self = this,
                page_num = page_number || self.page_number;
            this.file_content.getPage(page_num).then(function (page) {
                var viewport = page.getViewport(self.scale);
                self.canvas.width = viewport.width;
                self.canvas.height = viewport.height;

                var renderContext = {
                    canvasContext: self.ctx,
                    viewport: viewport
                };
                self.rendering = true;
                page.render(renderContext).then(function () {
                    self.rendering = false;
                    self.$('#page_number').val(page_num);
                    self.page_number = page_num;
                });
            });
        },
        next: function (ev) {
            ev.preventDefault();
            if (!this.is_loaded()) {
                return;
            }
            if (this.page_number === this.page_count) {
                this.fetch_next_slide();
            }
            if (this.page_number >= this.page_count) {
                return;
            }
            this.page_number += 1;
            if (!this.rendering) {
                this.render_page();
            }
        },
        fetch_next_slide: function () {
            var self = this,
                id = parseInt(this.id);
            openerp.jsonRpc('/slides/slide/' + id + '/overlay', 'call')
                .then(function (data) {
                    self.$(".oe_slides_pdf_suggestions").remove();
                    $(openerp.qweb.render("website.slide.overlay", {
                        slides: data
                    })).appendTo(self.$(".slide-wrapper"));
                    self.$('.oe_slides_pdf_js_thumb').hover(
                        function () {
                            $(this).find('.oe_slides_pdf_js_caption').stop().slideDown(250); //.fadeIn(250)
                        },
                        function () {
                            $(this).find('.oe_slides_pdf_js_caption').stop().slideUp(250); //.fadeOut(205)
                        }
                    );
                });
        },
        previous: function (ev) {
            ev.preventDefault();
            if (!this.is_loaded()) {
                return;
            }
            if (this.page_number <= 1) {
                return;
            }
            this.$(".oe_slides_pdf_suggestions").hide();
            this.page_number -= 1;
            if (!this.rendering) {
                this.render_page();
            }
        },
        first: function (ev) {
            ev.preventDefault();
            if (!this.is_loaded()) {
                return;
            }
            this.$(".oe_slides_pdf_suggestions").hide();
            this.page_number = 1;
            if (!this.rendering) {
                this.render_page();
            }
        },
        last: function (ev) {
            ev.preventDefault();
            if (!this.is_loaded()) {
                return;
            }
            this.page_number = this.page_count;
            if (!this.rendering) {
                this.render_page();
            }
        },
        fullscreen: function (ev) {
            ev.preventDefault();
            //TODO: Display warning when broswer not support native fullscreen API
            website.fullScreenAPI.requestFullScreen(this.canvas);
        },
        change_page_number: function (ev) {
            var page_asked = parseInt(ev.target.value, 10);
            this.page_number = (page_asked > 0 && page_asked <= this.page_count) ? page_asked : this.page_count;
            if (!this.rendering) {
                this.render_page();
            }
        }

    });

    //Export fullscreen Browser Compatible API to website namespace
    var fullScreenApi = {
            supportsFullScreen: false,
            isFullScreen: function () {
                return false;
            },
            requestFullScreen: function () {},
            cancelFullScreen: function () {},
            fullScreenEventName: '',
            prefix: ''
        },
        browserPrefixes = 'webkit moz o ms khtml'.split(' ');

    // check for native support
    if (typeof document.cancelFullScreen != 'undefined') {
        fullScreenApi.supportsFullScreen = true;
    } else {
        // check for fullscreen support by vendor prefix
        for (var i = 0, il = browserPrefixes.length; i < il; i++) {
            fullScreenApi.prefix = browserPrefixes[i];

            if (typeof document[fullScreenApi.prefix + 'CancelFullScreen'] != 'undefined') {
                fullScreenApi.supportsFullScreen = true;
                break;
            }
        }
    }

    if (fullScreenApi.supportsFullScreen) {
        fullScreenApi.fullScreenEventName = fullScreenApi.prefix + 'fullscreenchange';

        fullScreenApi.isFullScreen = function () {
            switch (this.prefix) {
            case '':
                return document.fullScreen;
            case 'webkit':
                return document.webkitIsFullScreen;
            default:
                return document[this.prefix + 'FullScreen'];
            }
        };
        fullScreenApi.requestFullScreen = function (el) {
            return (this.prefix === '') ? el.requestFullScreen() : el[this.prefix + 'RequestFullScreen']();
        };
        fullScreenApi.cancelFullScreen = function () {
            return (this.prefix === '') ? document.cancelFullScreen() : document[this.prefix + 'CancelFullScreen']();
        };
    }

    website.fullScreenAPI = fullScreenApi;
})();
