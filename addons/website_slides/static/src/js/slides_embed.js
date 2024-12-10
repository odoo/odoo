/**
 * This is a minimal version of the PDFViewer widget.
 * It is NOT use in the website_slides module, but it is called when embedding
 * a slide/video/document. This code can depend on pdf.js, JQuery and Bootstrap
 * (see website_slides.slide_embed_assets bundle, in website_slides_embed.xml)
 */
import { slideDown, slideToggle, slideUp } from "@web/core/utils/slide";

(function () {

    function debounce(func, timeout = 300){
        let timer;
        return (...args) => {
          clearTimeout(timer);
          timer = setTimeout(() => { func.apply(this, args); }, timeout);
        };
    }

    if (document.querySelector('#PDFViewer') && document.querySelector('#PDFViewerCanvas')) { // check if presentation only
        var MIN_ZOOM=1, MAX_ZOOM=10, ZOOM_INCREMENT=.5;

        // define embedded viewer (minimal object of the website.slide.PDFViewer widget)
        var EmbeddedViewer = function (viewerEl) {
            var self = this;
            this.viewer = viewerEl;
            this.slide_url = viewerEl.querySelector('#PDFSlideViewer').getAttribute('slideurl');
            this.slide_id = viewerEl.querySelector('#PDFSlideViewer').getAttribute('slideid');
            this.defaultpage = parseInt(viewerEl.querySelector('#PDFSlideViewer').getAttribute('defaultpage'));
            this.canvas = viewerEl.querySelector('canvas')[0];

            this.pdf_viewer = new globalThis.PDFSlidesViewer(this.slide_url, this.canvas);
            this.hasSuggestions = !!this.el.querySelectorAll(".oe_slides_suggestion_media").length;
            this.pdf_viewer.loadDocument().then(function () {
                self.on_loaded_file();
            });
        };
        EmbeddedViewer.prototype.__proto__ = {
            // jquery inside the object (like Widget)
            $: function (selector) {
                return this.$(this.viewer).find($(selector));
            },
            // post process action (called in '.then()')
            on_loaded_file: function () {
                this.el.querySelectorAll('canvas').forEach((el) => el.style.display = "block");
                this.el.querySelector('#page_count').textContent = this.pdf_viewer.pdf_page_total;
                this.el.querySelector('#PDFViewerLoader').style.display = "none";
                // init first page to display
                var initpage = this.defaultpage;
                var pageNum = (initpage > 0 && initpage <= this.pdf_viewer.pdf_page_total) ? initpage : 1;
                this.render_page(pageNum);
            },
            on_rendered_page: function (pageNumber) {
                if (pageNumber) {
                    this.el.querySelector('#page_number').value = pageNumber;
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
                var pageAsked = parseInt(this.el.querySelector('#page_number').value, 10);
                if (1 <= pageAsked && pageAsked <= this.pdf_viewer.pdf_page_total) {
                    this.pdf_viewer.changePage(pageAsked).then(this.on_rendered_page.bind(this));
                    this.navUpdate(pageAsked);
                } else {
                    // if page number out of range, reset the page_counter to the actual page
                    this.el.querySelector('#page_number').value = this.pdf_viewer.pdf_page_current;
                }
            },
            next: function () {
                if (
                    this.pdf_viewer.pdf_page_current >=
                    this.pdf_viewer.pdf_page_total + this.hasSuggestions
                ) {
                    return;
                }

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
                const slideSuggestOverlay = this.el.querySelector("#slide_suggest");
                if (!slideSuggestOverlay.classList.contains('d-none')) {
                    // Hide suggested slide overlay before changing page nb.
                    slideSuggestOverlay.addClass('d-none');
                    this.el.querySelector("#next").classList.remove("disabled");
                    if (this.pdf_viewer.pdf_page_total <= 1) {
                        this.el.querySelectorAll("#previous, #first").forEach((el) => el.add("disabled"));
                    }
                    return;
                }
                var self = this;
                this.pdf_viewer.previousPage().then(function (pageNum) {
                    if (pageNum) {
                        self.on_rendered_page(pageNum);
                    }
                    slideSuggestOverlay.addClass('d-none');
                });
            },
            first: function () {
                var self = this;
                this.pdf_viewer.firstPage().then(function (pageNum) {
                    self.on_rendered_page(pageNum);
                    self.el.querySelector("#slide_suggest").addClass('d-none');
                });
            },
            last: function () {
                var self = this;
                this.pdf_viewer.lastPage().then(function (pageNum) {
                    self.on_rendered_page(pageNum);
                    self.el.querySelector("#slide_suggest").addClass('d-none');
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
                const pagesCount = this.pdf_viewer.pdf_page_total + this.hasSuggestions;
                this.el.querySelector("#first").classList.toggle("disabled", pagesCount < 2 || pageNum < 2);
                this.el.querySelector("#last").classList.toggle(
                    "disabled",
                    pagesCount < 2 || pageNum >= this.pdf_viewer.pdf_page_total
                );
                this.el.querySelector("#next").classList.toggle("disabled", pageNum >= pagesCount);
                this.el.querySelector("#previous").classList.toggle("disabled", pageNum <= 1);
                this.el.querySelector("#zoomout").classList.toggle("disabled", this.pdf_viewer.pdf_zoom <= MIN_ZOOM);
                this.el.querySelector("#zoomin").classList.toggle("disabled", this.pdf_viewer.pdf_zoom >= MAX_ZOOM);
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
                this.el.querySelector("#slide_suggest").classList.remove("d-none");
                this.el.querySelectorAll("#next, #last").forEach((el) => el.classList.add("disabled"));
                this.el.querySelectorAll("#previous, #first").forEach((el) => el.classList.remove("disabled"));
            },
        };

        // embedded pdf viewer
        var embeddedViewer = new EmbeddedViewer(document.querySelector('#PDFViewer'));

        // bind the actions
        document.querySelector('#previous').addEventListener('click', function () {
            embeddedViewer.previous();
        });
        document.querySelector('#next').addEventListener('click', function () {
            embeddedViewer.next();
        });
        document.querySelector('#first').addEventListener('click', function () {
            embeddedViewer.first();
        });
        document.querySelector('#last').addEventListener('click', function () {
            embeddedViewer.last();
        });
        document.querySelector('#zoomin').addEventListener('click', function () {
            embeddedViewer.zoomIn();
        });
        document.querySelector('#zoomout').addEventListener('click', function () {
            embeddedViewer.zoomOut();
        });
        document.querySelector('#page_number').addEventListener('change', function () {
            embeddedViewer.change_page();
        });
        document.querySelector('#fullscreen').addEventListener('click', function () {
            embeddedViewer.fullscreen();
        });
        document.querySelector('#PDFViewer').addEventListener('click', function (ev) {
            embeddedViewer.fullScreenFooter(ev);
        });
        document.querySelector('#PDFViewer').addEventListener('wheel', function (ev) {
            if (ev.metaKey || ev.ctrlKey) {
                if (ev.originalEvent.deltaY > 0) {
                    embeddedViewer.zoomOut();
                } else if(ev.originalEvent.deltaY < 0) {
                    embeddedViewer.zoomIn();
                }
                return false;
            }
        });
        window.addEventListener("resize", debounce(() => {
            embeddedViewer.on_resize();
        }, 500));

        // switching slide with keyboard
        document.addEventListener("keydown", function (ev) {
            if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") {
                embeddedViewer.previous();
            }
            if (ev.key === "ArrowRight" || ev.key === "ArrowDown") {
                embeddedViewer.next();
            }
        });

        // display the option panels
        document.querySelector('.oe_slide_js_embed_option_link').on('click', function (ev) {
            ev.preventDefault();
            const toggleDiv = this.getAttribute('slide-option-id');
            document.querySelectorAll(".oe_slide_embed_option").forEach((el) => {
                if (el !== toggleDiv) {
                    el.style.display = "none";
                }
            })
            slideToggle(toggleDiv, 500);
        });

        // animation for the suggested slides
        document.querySelector(".oe_slides_suggestion_media").addEventListener("mouseenter", (ev) => {
            slideDown(ev.currentTarget.querySelector(".oe_slides_suggestion_caption"), 250);
        });
        document.querySelector(".oe_slides_suggestion_media").addEventListener("mouseleave", (ev) => {
            slideUp(ev.currentTarget.querySelector(".oe_slides_suggestion_caption"), 250);
        });

        // To avoid create a dependancy to openerpframework.js, we use JQuery AJAX to post data instead of ajax.jsonRpc
        document.querySelector('.oe_slide_js_share_email button').addEventListener('click', async function () {
            const widget = document.querySelector('.oe_slide_js_share_email');
            const input = widget.querySelector('input');
            const slideID = widget.querySelector('button').getAttribute('slide-id');
            if (input.value) {
                widget.classList.remove('o_has_error');
                widget.querySelectorAll('.form-control, .form-select').classList.remove('is-invalid');
                await fetch("/slides/slide/send_share_email", {
                    method: 'POST',
                    headers: {
                        'Content-Type': "application/json; charset=utf-8",
                    },
                    body: JSON.stringify({'jsonrpc': "2.0", 'method': "call", "params": {'slide_id': slideID, 'emails': input.val()}}),
                }).then(async (result) => {
                    const action = await result.json();
                    if (action.result) {
                        widget.querySelector('.alert-info').classList.remove('d-none');
                        widget.querySelector('.input-group').classList.add('d-none');
                    } else {
                        widget.querySelector('.alert-warning').removeClass('d-none');
                        widget.querySelector('.input-group').addClass('d-none');
                        widget.classList.add('o_has_error');
                        widget.querySelectorAll('.form-control, .form-select').forEach((el) => el.classList.add('is-invalid'));
                        input.focus();
                    }
                });
            } else {
                widget.querySelector('.alert-warning').classList.remove('d-none');
                widget.querySelector('.input-group').classList.add('d-none');
                widget.classList.add('o_has_error');
                widget.querySelectorAll('.form-control, .form-select').classList.add('is-invalid');
                input.focus();
            }
        });
    }
})();
