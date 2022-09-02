/* global PDFSlidesViewer */
/**
 * This is a minimal version of the PDFViewer widget.
 * It is NOT use in the website_slides module, but it is called when embedding
 * a slide/video/document. This code can depend on pdf.js, JQuery and Bootstrap
 * (see website_slides.slide_embed_assets bundle, in website_slides_embed.xml)
 */
$(function () {

    if ($('#PDFViewer') && $('#PDFViewerCanvas')) { // check if presentation only
        var MIN_ZOOM=1, MAX_ZOOM=10, ZOOM_INCREMENT=.5;

        // define embedded viewer (minimal object of the website.slide.PDFViewer widget)
        var EmbeddedViewer = function ($viewer) {
            var self = this;
            this.viewer = $viewer;
            this.slide_url = $viewer.find('#PDFSlideViewer').data('slideurl');
            this.slide_id = $viewer.find('#PDFSlideViewer').data('slideid');
            this.defaultpage = parseInt($viewer.find('#PDFSlideViewer').data('defaultpage'));
            this.canvas = $viewer.find('canvas')[0];

            this.pdf_viewer = new PDFSlidesViewer(this.slide_url, this.canvas, true);
            this.pdf_viewer.loadDocument().then(function () {
                self.on_loaded_file();
            });
        };
        EmbeddedViewer.prototype.__proto__ = {
            // jquery inside the object (like Widget)
            $: function (selector) {
                return this.viewer.find($(selector));
            },
            // post process action (called in '.then()')
            on_loaded_file: function () {
                this.$('canvas').show();
                this.$('#page_count').text(this.pdf_viewer.pdf_page_total);
                this.$('#PDFViewerLoader').hide();
                if (this.pdf_viewer.pdf_page_total > 1) {
                    this.$('.o_slide_navigation_buttons').removeClass('hide');
                }
                // init first page to display
                var initpage = this.defaultpage;
                var pageNum = (initpage > 0 && initpage <= this.pdf_viewer.pdf_page_total) ? initpage : 1;
                this.render_page(pageNum);
            },
            on_rendered_page: function (pageNumber) {
                if (pageNumber) {
                    this.$('#page_number').val(pageNumber);
                    this.navUpdate(pageNumber);
                }
            },
            on_resize: function() {
                this.render_page(this.pdf_viewer.pdf_page_current);
            },
            // page switching
            render_page: function (pageNumber) {
                this.pdf_viewer.queueRenderPage(pageNumber).then(this.on_rendered_page.bind(this));
                this.navUpdate(pageNumber);
            },
            change_page: function () {
                var pageAsked = parseInt(this.$('#page_number').val(), 10);
                if (1 <= pageAsked && pageAsked <= this.pdf_viewer.pdf_page_total) {
                    this.pdf_viewer.changePage(pageAsked).then(this.on_rendered_page.bind(this));
                    this.navUpdate(pageAsked);
                } else {
                    // if page number out of range, reset the page_counter to the actual page
                    this.$('#page_number').val(this.pdf_viewer.pdf_page_current);
                }
            },
            next: function () {
                var self = this;
                this.pdf_viewer.nextPage().then(function (pageNum) {
                    if (pageNum) {
                        self.on_rendered_page(pageNum);
                    } else {
                        if (self.pdf_viewer.pdf) { // avoid display suggestion when pdf is not loaded yet
                            self.display_suggested_slides();
                        }
                    }
                });
            },
            previous: function () {
                var self = this;
                this.pdf_viewer.previousPage().then(function (pageNum) {
                    if (pageNum) {
                        self.on_rendered_page(pageNum);
                    }
                    self.$("#slide_suggest").addClass('d-none');
                });
            },
            first: function () {
                var self = this;
                this.pdf_viewer.firstPage().then(function (pageNum) {
                    self.on_rendered_page(pageNum);
                    self.$("#slide_suggest").addClass('d-none');
                });
            },
            last: function () {
                var self = this;
                this.pdf_viewer.lastPage().then(function (pageNum) {
                    self.on_rendered_page(pageNum);
                    self.$("#slide_suggest").addClass('d-none');
                });
            },
            zoomIn: function() {
                if(this.pdf_viewer.pdf_zoom < MAX_ZOOM) {
                    this.pdf_viewer.pdf_zoom += ZOOM_INCREMENT;
                    this.render_page(this.pdf_viewer.pdf_page_current);
                }
            },
            zoomOut: function() {
                if(this.pdf_viewer.pdf_zoom > MIN_ZOOM) {
                    this.pdf_viewer.pdf_zoom -= ZOOM_INCREMENT;
                    this.render_page(this.pdf_viewer.pdf_page_current);
                }
            },
            navUpdate: function (pageNum) {
                this.$('#first').toggleClass('disabled', pageNum < 3 );
                this.$('#previous').toggleClass('disabled', pageNum < 2 );
                this.$('#next, #last').removeClass('disabled');
                this.$('#zoomout').toggleClass('disabled', this.pdf_viewer.pdf_zoom <= MIN_ZOOM);
                this.$('#zoomin').toggleClass('disabled', this.pdf_viewer.pdf_zoom >= MAX_ZOOM);
            },
            // full screen mode
            fullscreen: function () {
                this.pdf_viewer.toggleFullScreen();
            },
            fullScreenFooter: function (ev) {
                if (ev.target.id === "PDFViewerCanvas") {
                    this.pdf_viewer.toggleFullScreenFooter();
                }
            },
            // display suggestion displayed after last slide
            display_suggested_slides: function () {
                this.$("#slide_suggest").removeClass('d-none');
                this.$('#next, #last').addClass('disabled');
            },
        };

        // embedded pdf viewer
        var embeddedViewer = new EmbeddedViewer($('#PDFViewer'));

        // bind the actions
        $('#previous').on('click', function () {
            embeddedViewer.previous();
        });
        $('#next').on('click', function () {
            embeddedViewer.next();
        });
        $('#first').on('click', function () {
            embeddedViewer.first();
        });
        $('#last').on('click', function () {
            embeddedViewer.last();
        });
        $('#zoomin').on('click', function () {
            embeddedViewer.zoomIn();
        });
        $('#zoomout').on('click', function () {
            embeddedViewer.zoomOut();
        });
        $('#page_number').on('change', function () {
            embeddedViewer.change_page();
        });
        $('#fullscreen').on('click', function () {
            embeddedViewer.fullscreen();
        });
        $('#PDFViewer').on('click', function (ev) {
            embeddedViewer.fullScreenFooter(ev);
        });
        $('#PDFViewer').on('wheel', function (ev) {
            if (ev.metaKey || ev.ctrlKey) {
                if (ev.originalEvent.deltaY > 0) {
                    embeddedViewer.zoomOut();
                } else if(ev.originalEvent.deltaY < 0) {
                    embeddedViewer.zoomIn();
                }
                return false;
            }
        });
        $(window).on('resize', _.debounce(function() {
            embeddedViewer.on_resize();
        }, 500));

        // switching slide with keyboard
        $(document).keydown(function (ev) {
            if (ev.keyCode === 37 || ev.keyCode === 38) {
                embeddedViewer.previous();
            }
            if (ev.keyCode === 39 || ev.keyCode === 40) {
                embeddedViewer.next();
            }
        });

        // display the option panels
        $('.oe_slide_js_embed_option_link').on('click', function (ev) {
            ev.preventDefault();
            var toggleDiv = $(this).data('slide-option-id');
            $('.oe_slide_embed_option').not(toggleDiv).each(function () {
                $(this).hide();
            });
            $(toggleDiv).slideToggle();
        });

        // animation for the suggested slides
        $('.oe_slides_suggestion_media').hover(
            function () {
                $(this).find('.oe_slides_suggestion_caption').stop().slideDown(250);
            },
            function () {
                $(this).find('.oe_slides_suggestion_caption').stop().slideUp(250);
            }
        );

        // embed widget page selector
        $('.oe_slide_js_embed_code_widget input').on('change', function () {
            var page = parseInt($(this).val());
            if (!(page > 0 && page <= embeddedViewer.pdf_viewer.pdf_page_total)) {
                page = 1;
            }
            var actualCode = embeddedViewer.$('.slide_embed_code').val();
            var newCode = actualCode.replace(/(page=).*?([^\d]+)/, '$1' + page + '$2');
            embeddedViewer.$('.slide_embed_code').val(newCode);
        });

        // To avoid create a dependancy to openerpframework.js, we use JQuery AJAX to post data instead of ajax.jsonRpc
        $('.oe_slide_js_share_email button').on('click', function () {
            var widget = $('.oe_slide_js_share_email');
            var input = widget.find('input');
            var slideID = widget.find('button').data('slide-id');
            if (input.val()) {
                widget.removeClass('o_has_error').find('.form-control, .form-select').removeClass('is-invalid');
                $.ajax({
                    type: "POST",
                    dataType: 'json',
                    url: '/slides/slide/send_share_email',
                    contentType: "application/json; charset=utf-8",
                    data: JSON.stringify({'jsonrpc': "2.0", 'method': "call", "params": {'slide_id': slideID, 'emails': input.val()}}),
                    success: function (action) {
                        if (action.result) {
                            widget.find('.alert-info').removeClass('d-none');
                            widget.find('.input-group').addClass('d-none');
                        } else {
                            widget.find('.alert-warning').removeClass('d-none');
                            widget.find('.input-group').addClass('d-none');
                            widget.addClass('o_has_error').find('.form-control, .form-select').addClass('is-invalid');
                            input.focus();
                        }
                    },
                });
            } else {
                widget.find('.alert-warning').removeClass('d-none');
                widget.find('.input-group').addClass('d-none');
                widget.addClass('o_has_error').find('.form-control, .form-select').addClass('is-invalid');
                input.focus();
            }
        });
    }
});
