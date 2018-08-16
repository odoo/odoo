/*global $, _, PDFSlidesViewer*/

/**
This file is a minimal version of the PDFViewer widget.
It is NOT use in the website_slides module, but it is
called when embedding a slide/video/document.
This code can depend on pdf.js, JQuery and Bootstrap
(see website_slides.slide_embed_assets bundle, in website_slides_embed.xml)
**/
$(document).ready(function () {

    if($('#PDFViewer') && $('#PDFViewerCanvas')){ // check if presentation only

        // define embedded viewer (minimal object of the website.slide.PDFViewer widget)
        var EmbeddedViewer = function($viewer){
            var self = this;
            this.viewer = $viewer;
            this.slide_url = $viewer.find('#PDFSlideViewer').data('slideurl');
            this.slide_id = $viewer.find('#PDFSlideViewer').data('slideid');
            this.defaultpage = parseInt($viewer.find('#PDFSlideViewer').data('defaultpage'));
            this.canvas = $viewer.find('canvas')[0];

            this.pdf_viewer = new PDFSlidesViewer(this.slide_url, this.canvas, true);
            this.pdf_viewer.loadDocument().then(function(file_content){
                self.on_loaded_file();
            });
        };
        EmbeddedViewer.prototype.__proto__ = {
            // jquery inside the object (like Widget)
            $: function(selector){
                return this.viewer.find($(selector));
            },
            // post process action (called in '.then()')
            on_loaded_file: function(){
                this.$('canvas').show();
                this.$('#page_count').text(this.pdf_viewer.pdf_page_total);
                this.$('#PDFViewerLoader').hide();
                if (this.pdf_viewer.pdf_page_total > 1) {
                    this.$('.o_slide_navigation_buttons').removeClass('hide');
                }
                // init first page to display
                var initpage = this.defaultpage;
                var pageNum = (initpage > 0 && initpage <= this.pdf_viewer.pdf_page_total)? initpage : 1;
                this.render_page(pageNum);
            },
            on_rendered_page: function(page_number){
                if(page_number){
                    this.$('#page_number').val(page_number);
                }
            },
            // page switching
            render_page: function (page_number) {
                this.pdf_viewer.renderPage(page_number).then(this.on_rendered_page.bind(this));
            },
            change_page: function () {
                var page_asked = parseInt(this.$('#page_number').val(), 10);
                if(1 <= page_asked && page_asked <= this.pdf_viewer.pdf_page_total){
                    this.pdf_viewer.changePage(page_asked).then(this.on_rendered_page.bind(this));
                }else{
                    // if page number out of range, reset the page_counter to the actual page
                    this.$('#page_number').val(this.pdf_viewer.pdf_page_current);
                }
            },
            next: function () {
                var self = this;
                this.pdf_viewer.nextPage().then(function(page_num){
                    if(page_num){
                        self.on_rendered_page(page_num);
                    }else{
                        if(self.pdf_viewer.pdf){ // avoid display suggestion when pdf is not loaded yet
                            self.display_suggested_slides();
                        }
                    }
                });
            },
            previous: function () {
                var self = this;
                this.pdf_viewer.previousPage().then(function(page_num){
                    if(page_num){
                        self.on_rendered_page(page_num);
                    }
                    self.$("#slide_suggest").hide();
                });
            },
            first: function () {
                var self = this;
                this.pdf_viewer.firstPage().then(function(page_num){
                    self.on_rendered_page(page_num);
                    self.$("#slide_suggest").hide();
                });
            },
            last: function () {
                var self = this;
                this.pdf_viewer.lastPage().then(function(page_num){
                    self.on_rendered_page(page_num);
                    self.$("#slide_suggest").hide();
                });
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
                this.$("#slide_suggest").show();
            },
        };

        // embedded pdf viewer
        var embedded_viewer = new EmbeddedViewer($('#PDFViewer'));

        // bind the actions
        $('#previous').on('click', function(){
            embedded_viewer.previous();
        });
        $('#next').on('click', function(){
            embedded_viewer.next();
        });
        $('#first').on('click', function(){
            embedded_viewer.first();
        });
        $('#last').on('click', function(){
            embedded_viewer.last();
        });
        $('#page_number').on('change', function(){
            embedded_viewer.change_page();
        });
        $('#fullscreen').on('click',function(){
            embedded_viewer.fullscreen();
        });
        $('#PDFViewer').on('click',function (ev){
            embedded_viewer.fullScreenFooter(ev);
        });

        // switching slide with keyboard
        $(document).keydown(function (ev) {
            if (ev.keyCode === 37 || ev.keyCode === 38) {
                embedded_viewer.previous();
            }
            if (ev.keyCode === 39 || ev.keyCode === 40) {
                 embedded_viewer.next();
            }
        });

        // display the option panels
        $('.oe_slide_js_embed_option_link').on('click', function (ev) {
            ev.preventDefault();
            var toggleDiv = $(this).data('slide-option-id');
            $('.oe_slide_embed_option').not(toggleDiv).each(function() {
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
            if (!(page > 0 && page <= embedded_viewer.pdf_viewer.pdf_page_total)) {
                page = 1;
            }
            var actual_code = embedded_viewer.$('.slide_embed_code').val();
            var new_code = actual_code.replace(/(page=).*?([^\d]+)/, '$1' + page + '$2');
            embedded_viewer.$('.slide_embed_code').val(new_code);
        });

        // To avoid create a dependancy to openerpframework.js, we use JQuery AJAX to post data instead of ajax.jsonRpc
        $('.oe_slide_js_share_email button').on('click', function () {
            var widget = $('.oe_slide_js_share_email');
            var input = widget.find('input');
            var slide_id = widget.find('button').data('slide-id');
            if(input.val() && input[0].checkValidity()){
                widget.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
                $.ajax({
                    type: "POST",
                    dataType: 'json',
                    url: '/slides/slide/send_share_email',
                    contentType: "application/json; charset=utf-8",
                    data: JSON.stringify({'jsonrpc': "2.0", 'method': "call", "params": {'slide_id': slide_id, 'email': input.val()}}),
                    success: function () {
                        widget.html($('<div class="alert alert-info" role="alert"><strong>Thank you!</strong> Mail has been sent.</div>'));
                    },
                    error: function(data){
                        console.log("ERROR ", data);
                    }
                });
            }else{
                widget.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
                input.focus();
            }
        });
    }
});


