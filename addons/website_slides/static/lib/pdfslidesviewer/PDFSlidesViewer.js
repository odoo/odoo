/**
    Homemade helper for browsing PDF document from page to page.
    This is hightly inspired from https://github.com/mozilla/pdf.js/blob/master/examples/learning/prevnext.html
    This lib requires PDF JS. It simply uses PDFjs and its promises.
    DOC : http://mozilla.github.io/pdf.js/api/draft/api.js.html
*/

// !!!!!!!!! use window.PDFJS and not PDFJS

var PDFSlidesViewer = (function(){

    function PDFSlidesViewer(pdf_url, $canvas, disableWorker){
        // pdf variables
        this.pdf = null;
        this.pdf_url = pdf_url || false;
        this.pdf_scale = 1.5;
        this.pdf_page_total = 0;
        this.pdf_page_current = 1; // default is the first page
        // promise business
        this.pageRendering = false;
        this.pageNumPending = null;
        //canvas
        this.canvas = $canvas;
        this.canvas_context = $canvas.getContext('2d');
        // PDF JS business
        /**
         * Disable the web worker and run all code on the main thread. This will happen
         * automatically if the browser doesn't support workers or sending typed arrays
         * to workers.
         * @var {boolean}
         *
         * disableWorker should be 'true' if the document came from another origin than the
         * page (typically the 'embed case').
         * @see http://en.wikipedia.org/wiki/Cross-origin_resource_sharing.
         * this is equivalent to the use_cors option in openerpframework.js
         */
        window.PDFJS.disableWorker = disableWorker || false;
    };

    /**
     * Load the PDF document
     * @param (optional) url : the url of the document to load
     */
    PDFSlidesViewer.prototype.loadDocument = function(url) {
        var self = this;
        var pdf_url = url || this.pdf_url;
        return window.PDFJS.getDocument(pdf_url).then(function (file_content) {
            self.pdf = file_content;
            self.pdf_page_total = file_content.numPages;
            return file_content;
        });
    };

    /**
     * Get page info from document, resize canvas accordingly, and render page.
     * @param page_number : Page number.
     */
    PDFSlidesViewer.prototype.renderPage = function(page_number) {
        var self = this;
        this.pageRendering = true;
        return this.pdf.getPage(page_number).then(function(page) {
            // Each PDF page has its own viewport which defines the size in pixels and initial rotation.
            var viewport = page.getViewport(self.pdf_scale);
            self.canvas.height = viewport.height;
            self.canvas.width = viewport.width;
            // Render PDF page into canvas context
            var renderContext = {
                canvasContext: self.canvas_context,
                viewport: viewport
            };
            var renderTask = page.render(renderContext);
            // Wait for rendering to finish
            return renderTask.promise.then(function () {
                self.pageRendering = false;
                if (self.pageNumPending !== null) {
                    // New page rendering is pending
                    renderPage(self.pageNumPending);
                    self.pageNumPending = null;
                }
                self.pdf_page_current = page_number;
                return page_number;
            });
        });
    };

    /**
     * If another page rendering in progress, waits until the rendering is
     * finised. Otherwise, executes rendering immediately.
     */
    PDFSlidesViewer.prototype.queueRenderPage = function(num) {
        if(this.pageRendering) {
            this.pageNumPending = num; // the queue is only the last elem
            return Promise.resolve(num);
        } else {
            return this.renderPage(num);
        }
    }

    /**
     * Displays previous page.
     */
    PDFSlidesViewer.prototype.previousPage = function() {
        if (this.pdf_page_current <= 1) {
          return Promise.resolve(false);
        }
        this.pdf_page_current--;
        return this.queueRenderPage(this.pdf_page_current);
    };

    /**
     * Displays next page.
     */
    PDFSlidesViewer.prototype.nextPage = function() {
        if (this.pdf_page_current >= this.pdf_page_total) {
            return Promise.resolve(false);
        }
        this.pdf_page_current++;
        return this.queueRenderPage(this.pdf_page_current);
    };

    /**
     * Displays the given page.
     */
    PDFSlidesViewer.prototype.changePage = function(num){
        if(1 <= num <= this.pdf_page_total){
            this.pdf_page_current = num;
            return this.queueRenderPage(num);
        }
        return Promise.resolve(false);
    }

    /**
     * Displays first page.
     */
    PDFSlidesViewer.prototype.firstPage = function(){
        this.pdf_page_current = 1;
        return this.queueRenderPage(1);
    }

    /**
     * Displays last page.
     */
    PDFSlidesViewer.prototype.lastPage = function(){
        this.pdf_page_current = this.pdf_page_total;
        return this.queueRenderPage(this.pdf_page_total);
    }

    PDFSlidesViewer.prototype.toggleFullScreenFooter = function(){
        if(document.fullscreenElement || document.mozFullScreenElement || document.webkitFullscreenElement || document.msFullscreenElement) {
            $('div#PDFViewer > div.navbar-fixed-bottom').toggleClass('oe_show_footer');
        }
    }

    PDFSlidesViewer.prototype.toggleFullScreen = function(){
        var el = this.canvas.parentNode;

        var isFullscreenAvailable = document.fullscreenEnabled || document.mozFullScreenEnabled || document.webkitFullscreenEnabled || document.msFullscreenEnabled || false;
        if(isFullscreenAvailable){ // Full screen supported
            // get the actual element in FullScreen mode (Null if no element)
            var fullscreenElement = document.fullscreenElement || document.mozFullScreenElement || document.webkitFullscreenElement || document.msFullscreenElement;

            if (fullscreenElement) { // Exit the full screen mode
                if (document.exitFullscreen) {
                    // W3C standard
                    document.exitFullscreen();
                } else if (document.mozCancelFullScreen) {
                    // Firefox 10+, Firefox for Android
                    document.mozCancelFullScreen();
                } else if (document.webkitExitFullscreen) {
                    // Chrome 20+, Safari 6+, Opera 15+, Chrome for Android, Opera Mobile 16+
                    document.webkitExitFullscreen();
                } else if (document.webkitCancelFullScreen) {
                    // Chrome 15+, Safari 5.1+
                    document.webkitCancelFullScreen();
                } else if (document.msExitFullscreen) {
                    // IE 11+
                    document.msExitFullscreen();
                }
            }else { // Request to put the 'el' element in FullScreen mode
                if (el.requestFullscreen) {
                    // W3C standard
                    el.requestFullscreen();
                } else if (el.mozRequestFullScreen) {
                    // Firefox 10+, Firefox for Android
                    el.mozRequestFullScreen();
                } else if (el.msRequestFullscreen) {
                    // IE 11+
                    el.msRequestFullscreen();
                } else if (el.webkitRequestFullscreen) {
                    if (navigator.userAgent.indexOf('Safari') != -1 && navigator.userAgent.indexOf('Chrome') == -1) {
                        // Safari 6+
                        el.webkitRequestFullscreen();
                    } else {
                        // Chrome 20+, Opera 15+, Chrome for Android, Opera Mobile 16+
                        el.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
                    }
                } else if (el.webkitRequestFullScreen) {
                    if (navigator.userAgent.indexOf('Safari') != -1 && navigator.userAgent.indexOf('Chrome') == -1) {
                        // Safari 5.1+
                        el.webkitRequestFullScreen();
                    } else {
                        // Chrome 15+
                        el.webkitRequestFullScreen(Element.ALLOW_KEYBOARD_INPUT);
                    }
                }
            }
        }else{
            // Full screen not supported by the browser
            console.error("ERROR : full screen not supported by web browser");
        }
    }
    return PDFSlidesViewer;
})();
