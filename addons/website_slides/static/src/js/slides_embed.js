// @odoo-module ignore
/**
 * Minimal PDFViewer widget (vanilla JS version)
 */
document.addEventListener("DOMContentLoaded", () => {
    function debounce(func, timeout = 300) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => func.apply(this, args), timeout);
        };
    }

    const viewerEl = document.querySelector("#PDFViewer");
    const canvasEl = document.querySelector("#PDFViewerCanvas");

    if (!viewerEl || !canvasEl) {
        return;
    }

    const MIN_ZOOM = 1;
    const MAX_ZOOM = 10;
    const ZOOM_INCREMENT = 0.5;

    function EmbeddedViewer(viewer) {
        this.viewer = viewer;
        const slideViewer = viewer.querySelector("#PDFSlideViewer");

        this.slide_url = slideViewer.dataset.slideurl;
        this.slide_id = slideViewer.dataset.slideid;
        this.defaultpage = parseInt(slideViewer.dataset.defaultpage, 10);
        this.canvas = viewer.querySelector("canvas");

        this.pdf_viewer = new globalThis.PDFSlidesViewer(this.slide_url, this.canvas);
        this.hasSuggestions = !!viewer.querySelector(".oe_slides_suggestion_media");

        this.pdf_viewer.loadDocument().then(() => {
            this.on_loaded_file();
        });
    }

    EmbeddedViewer.prototype = {
        on_loaded_file() {
            this.viewer.querySelector("canvas").style.display = "";
            this.viewer.querySelector("#page_count").textContent = this.pdf_viewer.pdf_page_total;
            this.viewer.querySelector("#PDFViewerLoader").style.display = "none";

            const initPage =
                this.defaultpage > 0 && this.defaultpage <= this.pdf_viewer.pdf_page_total
                    ? this.defaultpage
                    : 1;

            this.render_page(initPage);
        },

        on_rendered_page(pageNumber) {
            if (pageNumber) {
                this.viewer.querySelector("#page_number").value = pageNumber;
                this.navUpdate(pageNumber);
            }
        },

        on_resize() {
            this.render_page(this.pdf_viewer.pdf_page_current);
        },

        render_page(pageNumber) {
            this.pdf_viewer.queueRenderPage(pageNumber).then(this.on_rendered_page.bind(this));
            this.navUpdate(pageNumber);
        },

        change_page() {
            const pageAsked = parseInt(this.viewer.querySelector("#page_number").value, 10);
            if (pageAsked >= 1 && pageAsked <= this.pdf_viewer.pdf_page_total) {
                this.pdf_viewer.changePage(pageAsked).then(this.on_rendered_page.bind(this));
            } else {
                this.viewer.querySelector("#page_number").value = this.pdf_viewer.pdf_page_current;
            }
        },

        next() {
            if (
                this.pdf_viewer.pdf_page_current >=
                this.pdf_viewer.pdf_page_total + this.hasSuggestions
            ) {
                return;
            }

            this.pdf_viewer.nextPage().then((pageNum) => {
                if (pageNum) {
                    this.on_rendered_page(pageNum);
                } else if (this.pdf_viewer.pdf) {
                    this.display_suggested_slides();
                }
            });
        },

        previous() {
            const suggest = this.viewer.querySelector("#slide_suggest");

            if (!suggest.classList.contains("d-none")) {
                suggest.classList.add("d-none");
                this.viewer.querySelector("#next").classList.remove("disabled");

                if (this.pdf_viewer.pdf_page_total <= 1) {
                    this.viewer.querySelector("#previous").classList.add("disabled");
                    this.viewer.querySelector("#first").classList.add("disabled");
                }
                return;
            }

            this.pdf_viewer.previousPage().then((pageNum) => {
                if (pageNum) {
                    this.on_rendered_page(pageNum);
                }
                suggest.classList.add("d-none");
            });
        },

        first() {
            this.pdf_viewer.firstPage().then((pageNum) => {
                this.on_rendered_page(pageNum);
                this.viewer.querySelector("#slide_suggest").classList.add("d-none");
            });
        },

        last() {
            this.pdf_viewer.lastPage().then((pageNum) => {
                this.on_rendered_page(pageNum);
                this.viewer.querySelector("#slide_suggest").classList.add("d-none");
            });
        },

        zoomIn() {
            if (this.pdf_viewer.pdf_zoom < MAX_ZOOM) {
                this.pdf_viewer.pdf_zoom += ZOOM_INCREMENT;
                this.render_page(this.pdf_viewer.pdf_page_current);
            }
        },

        zoomOut() {
            if (this.pdf_viewer.pdf_zoom > MIN_ZOOM) {
                this.pdf_viewer.pdf_zoom -= ZOOM_INCREMENT;
                this.render_page(this.pdf_viewer.pdf_page_current);
            }
        },

        navUpdate(pageNum) {
            const pagesCount = this.pdf_viewer.pdf_page_total + this.hasSuggestions;

            this.viewer
                .querySelector("##first")
                .classList.toggle("disabled", pagesCount < 2 || pageNum < 2);
            this.viewer
                .querySelector("#last")
                .classList.toggle(
                    "disabled",
                    pagesCount < 2 || pageNum >= this.pdf_viewer.pdf_page_total
                );
            this.viewer.querySelector("#next").classList.toggle("disabled", pageNum >= pagesCount);
            this.viewer.querySelector("#previous").classList.toggle("disabled", pageNum <= 1);
            this.viewer
                .querySelector("#zoomout")
                .classList.toggle("disabled", this.pdf_viewer.pdf_zoom <= MIN_ZOOM);
            this.viewer
                .querySelector("#zoomin")
                .classList.toggle("disabled", this.pdf_viewer.pdf_zoom >= MAX_ZOOM);
        },

        fullscreen() {
            this.pdf_viewer.toggleFullScreen();
        },

        fullScreenFooter(ev) {
            if (ev.target.id === "PDFViewerCanvas") {
                this.pdf_viewer.toggleFullScreenFooter();
            }
        },

        display_suggested_slides() {
            this.viewer.querySelector("#slide_suggest").classList.remove("d-none");
            this.viewer.querySelector("#next").classList.add("disabled");
            this.viewer.querySelector("#last").classList.add("disabled");
            this.viewer.querySelector("#previous").classList.remove("disabled");
            this.viewer.querySelector("#first").classList.remove("disabled");
        },
    };

    const embeddedViewer = new EmbeddedViewer(viewerEl);

    document.querySelector("#previous").addEventListener("click", () => embeddedViewer.previous());
    document.querySelector("#next").addEventListener("click", () => embeddedViewer.next());
    document.querySelector("#first").addEventListener("click", () => embeddedViewer.first());
    document.querySelector("#last").addEventListener("click", () => embeddedViewer.last());
    document.querySelector("#zoomin").addEventListener("click", () => embeddedViewer.zoomIn());
    document.querySelector("#zoomout").addEventListener("click", () => embeddedViewer.zoomOut());
    document
        .querySelector("#page_number")
        .addEventListener("change", () => embeddedViewer.change_page());
    document
        .querySelector("#fullscreen")
        .addEventListener("click", () => embeddedViewer.fullscreen());

    viewerEl.addEventListener("click", (ev) => embeddedViewer.fullScreenFooter(ev));

    viewerEl.addEventListener("wheel", (ev) => {
        if (ev.ctrlKey || ev.metaKey) {
            ev.preventDefault();
            ev.deltaY > 0 ? embeddedViewer.zoomOut() : embeddedViewer.zoomIn();
        }
    });

    window.addEventListener(
        "resize",
        debounce(() => embeddedViewer.on_resize(), 500)
    );

    document.addEventListener("keydown", (ev) => {
        if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") {
            embeddedViewer.previous();
        }
        if (ev.key === "ArrowRight" || ev.key === "ArrowDown") {
            embeddedViewer.next();
        }
    });
});
