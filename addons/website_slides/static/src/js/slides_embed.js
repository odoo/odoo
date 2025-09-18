// @odoo-module ignore
/**
 * Minimal PDFViewer widget for embedded slide/video/document viewing.
 * Not used in the website_slides module directly — called when embedding
 * a slide. Depends on pdf.js and Bootstrap (see website_slides.slide_embed_assets
 * bundle in website_slides_embed.xml).
 */
document.addEventListener('DOMContentLoaded', function () {

    function debounce(func, timeout = 300) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => { func.apply(this, args); }, timeout);
        };
    }

    var pdfViewer = document.getElementById('PDFViewer');
    var pdfViewerCanvas = document.getElementById('PDFViewerCanvas');

    if (pdfViewer && pdfViewerCanvas) { // check if presentation only
        var MIN_ZOOM = 1, MAX_ZOOM = 10, ZOOM_INCREMENT = .5;

        // define embedded viewer (minimal object of the website.slide.PDFViewer widget)
        var EmbeddedViewer = function (viewer) {
            var self = this;
            this.viewer = viewer;
            var slideViewerEl = viewer.querySelector('#PDFSlideViewer');
            this.slide_url = slideViewerEl.dataset.slideurl;
            this.slide_id = slideViewerEl.dataset.slideid;
            this.defaultpage = parseInt(slideViewerEl.dataset.defaultpage);
            this.canvas = viewer.querySelector('canvas');

            this.pdf_viewer = new globalThis.PDFSlidesViewer(this.slide_url, this.canvas);
            this.hasSuggestions = !!this.viewer.querySelector(".oe_slides_suggestion_media");
            this.pdf_viewer.loadDocument().then(function () {
                self.on_loaded_file();
            });
        };
        EmbeddedViewer.prototype.__proto__ = {
            // querySelector inside the viewer element (like Widget.$)
            $: function (selector) {
                return this.viewer.querySelector(selector);
            },
            // post process action (called in '.then()')
            on_loaded_file: function () {
                this.$('canvas').style.display = '';
                this.$('#page_count').textContent = this.pdf_viewer.pdf_page_total;
                this.$('#PDFViewerLoader').style.display = 'none';
                // init first page to display
                var initpage = this.defaultpage;
                var pageNum = (initpage > 0 && initpage <= this.pdf_viewer.pdf_page_total) ? initpage : 1;
                this.render_page(pageNum);
            },
            on_rendered_page: function (pageNumber) {
                if (pageNumber) {
                    this.$('#page_number').value = pageNumber;
                    this.navUpdate(pageNumber);
                }
            },
            on_resize: function () {
                this.render_page(this.pdf_viewer.pdf_page_current);
            },
            // page switching
            render_page: function (pageNumber) {
                this.pdf_viewer.queueRenderPage(pageNumber).then(this.on_rendered_page.bind(this));
                this.navUpdate(pageNumber);
            },
            change_page: function () {
                var pageAsked = parseInt(this.$('#page_number').value, 10);
                if (1 <= pageAsked && pageAsked <= this.pdf_viewer.pdf_page_total) {
                    this.pdf_viewer.changePage(pageAsked).then(this.on_rendered_page.bind(this));
                    this.navUpdate(pageAsked);
                } else {
                    // if page number out of range, reset the page_counter to the actual page
                    this.$('#page_number').value = this.pdf_viewer.pdf_page_current;
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
                var slideSuggestOverlay = this.$("#slide_suggest");
                if (slideSuggestOverlay && !slideSuggestOverlay.classList.contains('d-none')) {
                    // Hide suggested slide overlay before changing page nb.
                    slideSuggestOverlay.classList.add('d-none');
                    this.$("#next").classList.remove("disabled");
                    if (this.pdf_viewer.pdf_page_total <= 1) {
                        this.$("#previous").classList.add("disabled");
                        this.$("#first").classList.add("disabled");
                    }
                    return;
                }
                var self = this;
                this.pdf_viewer.previousPage().then(function (pageNum) {
                    if (pageNum) {
                        self.on_rendered_page(pageNum);
                    }
                    if (slideSuggestOverlay) {
                        slideSuggestOverlay.classList.add('d-none');
                    }
                });
            },
            first: function () {
                var self = this;
                this.pdf_viewer.firstPage().then(function (pageNum) {
                    self.on_rendered_page(pageNum);
                    var el = self.$("#slide_suggest");
                    if (el) {
                        el.classList.add('d-none');
                    }
                });
            },
            last: function () {
                var self = this;
                this.pdf_viewer.lastPage().then(function (pageNum) {
                    self.on_rendered_page(pageNum);
                    var el = self.$("#slide_suggest");
                    if (el) {
                        el.classList.add('d-none');
                    }
                });
            },
            zoomIn: function () {
                if (this.pdf_viewer.pdf_zoom < MAX_ZOOM) {
                    this.pdf_viewer.pdf_zoom += ZOOM_INCREMENT;
                    this.render_page(this.pdf_viewer.pdf_page_current);
                }
            },
            zoomOut: function () {
                if (this.pdf_viewer.pdf_zoom > MIN_ZOOM) {
                    this.pdf_viewer.pdf_zoom -= ZOOM_INCREMENT;
                    this.render_page(this.pdf_viewer.pdf_page_current);
                }
            },
            navUpdate: function (pageNum) {
                var pagesCount = this.pdf_viewer.pdf_page_total + this.hasSuggestions;
                this.$("#first").classList.toggle("disabled", pagesCount < 2 || pageNum < 2);
                this.$("#last").classList.toggle(
                    "disabled",
                    pagesCount < 2 || pageNum >= this.pdf_viewer.pdf_page_total
                );
                this.$("#next").classList.toggle("disabled", pageNum >= pagesCount);
                this.$("#previous").classList.toggle("disabled", pageNum <= 1);
                this.$("#zoomout").classList.toggle("disabled", this.pdf_viewer.pdf_zoom <= MIN_ZOOM);
                this.$("#zoomin").classList.toggle("disabled", this.pdf_viewer.pdf_zoom >= MAX_ZOOM);
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
                var suggestEl = this.$("#slide_suggest");
                if (suggestEl) {
                    suggestEl.classList.remove("d-none");
                }
                var nextEl = this.$("#next");
                if (nextEl) {
                    nextEl.classList.add("disabled");
                }
                var lastEl = this.$("#last");
                if (lastEl) {
                    lastEl.classList.add("disabled");
                }
                var prevEl = this.$("#previous");
                if (prevEl) {
                    prevEl.classList.remove("disabled");
                }
                var firstEl = this.$("#first");
                if (firstEl) {
                    firstEl.classList.remove("disabled");
                }
            },
        };

        // embedded pdf viewer
        var embeddedViewer = new EmbeddedViewer(pdfViewer);

        // bind the actions
        document.getElementById('previous').addEventListener('click', function () {
            embeddedViewer.previous();
        });
        document.getElementById('next').addEventListener('click', function () {
            embeddedViewer.next();
        });
        document.getElementById('first').addEventListener('click', function () {
            embeddedViewer.first();
        });
        document.getElementById('last').addEventListener('click', function () {
            embeddedViewer.last();
        });
        document.getElementById('zoomin').addEventListener('click', function () {
            embeddedViewer.zoomIn();
        });
        document.getElementById('zoomout').addEventListener('click', function () {
            embeddedViewer.zoomOut();
        });
        document.getElementById('page_number').addEventListener('change', function () {
            embeddedViewer.change_page();
        });
        document.getElementById('fullscreen').addEventListener('click', function () {
            embeddedViewer.fullscreen();
        });
        pdfViewer.addEventListener('click', function (ev) {
            embeddedViewer.fullScreenFooter(ev);
        });
        pdfViewer.addEventListener('wheel', function (ev) {
            if (ev.metaKey || ev.ctrlKey) {
                if (ev.deltaY > 0) {
                    embeddedViewer.zoomOut();
                } else if (ev.deltaY < 0) {
                    embeddedViewer.zoomIn();
                }
                ev.preventDefault();
                return;
            }
        });
        window.addEventListener('resize', debounce(function () {
            embeddedViewer.on_resize();
        }, 500));

        // switching slide with keyboard
        document.addEventListener('keydown', function (ev) {
            if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") {
                embeddedViewer.previous();
            }
            if (ev.key === "ArrowRight" || ev.key === "ArrowDown") {
                embeddedViewer.next();
            }
        });

        // display the option panels
        for (var link of document.querySelectorAll('.oe_slide_js_embed_option_link')) {
            link.addEventListener('click', function (ev) {
                ev.preventDefault();
                var toggleId = this.dataset.slideOptionId;
                var toggleEl = toggleId ? document.querySelector(toggleId) : null;
                // Hide other option panels
                for (var opt of document.querySelectorAll('.oe_slide_embed_option')) {
                    if (opt !== toggleEl) {
                        opt.style.display = 'none';
                    }
                }
                // Toggle the target panel
                if (toggleEl) {
                    toggleEl.style.display = toggleEl.style.display === 'none' ? '' : 'none';
                }
            });
        }

        // animation for the suggested slides
        for (var media of document.querySelectorAll('.oe_slides_suggestion_media')) {
            var caption = media.querySelector('.oe_slides_suggestion_caption');
            if (!caption) {
                continue;
            }
            // Set up transition styles for slide animation
            caption.style.overflow = 'hidden';
            caption.style.transition = 'max-height 250ms ease, opacity 250ms ease';
            caption.style.maxHeight = '0';
            caption.style.opacity = '0';

            media.addEventListener('mouseenter', function () {
                var cap = this.querySelector('.oe_slides_suggestion_caption');
                if (cap) {
                    cap.style.maxHeight = cap.scrollHeight + 'px';
                    cap.style.opacity = '1';
                }
            });
            media.addEventListener('mouseleave', function () {
                var cap = this.querySelector('.oe_slides_suggestion_caption');
                if (cap) {
                    cap.style.maxHeight = '0';
                    cap.style.opacity = '0';
                }
            });
        }

        // Use fetch instead of jQuery AJAX to post data
        var shareBtn = document.querySelector('.oe_slide_js_share_email button');
        if (shareBtn) {
            shareBtn.addEventListener('click', function () {
                var widget = document.querySelector('.oe_slide_js_share_email');
                var input = widget.querySelector('input');
                var slideID = widget.querySelector('button').dataset.slideId;
                if (input.value) {
                    widget.classList.remove('o_has_error');
                    for (var ctrl of widget.querySelectorAll('.form-control, .form-select')) {
                        ctrl.classList.remove('is-invalid');
                    }
                    fetch('/slides/slide/send_share_email', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json; charset=utf-8' },
                        body: JSON.stringify({
                            jsonrpc: '2.0',
                            method: 'call',
                            params: { slide_id: slideID, emails: input.value },
                        }),
                    })
                    .then(function (response) { return response.json(); })
                    .then(function (action) {
                        if (action.result) {
                            widget.querySelector('.alert-info').classList.remove('d-none');
                            widget.querySelector('.input-group').classList.add('d-none');
                        } else {
                            widget.querySelector('.alert-warning').classList.remove('d-none');
                            widget.querySelector('.input-group').classList.add('d-none');
                            widget.classList.add('o_has_error');
                            for (var ctrl of widget.querySelectorAll('.form-control, .form-select')) {
                                ctrl.classList.add('is-invalid');
                            }
                            input.focus();
                        }
                    });
                } else {
                    widget.querySelector('.alert-warning').classList.remove('d-none');
                    widget.querySelector('.input-group').classList.add('d-none');
                    widget.classList.add('o_has_error');
                    for (var ctrl of widget.querySelectorAll('.form-control, .form-select')) {
                        ctrl.classList.add('is-invalid');
                    }
                    input.focus();
                }
            });
        }
    }
});
