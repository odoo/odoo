import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { SlideShareDialog } from "../js/public/components/slide_share_dialog/slide_share_dialog";
import { Mutex } from "@web/core/utils/concurrency";

export class SlidesEmbed extends Interaction {
    static selector = "#PDFViewer";
    static selectorHas = "#PDFSlideViewer > #PDFViewerCanvas";
    dynamicContent = {
        _root: {
            "t-on-wheel": async (ev) => {
                if (!(ev.metaKey || ev.ctrlKey)) {
                    return;
                }
                ev.preventDefault();
                const container = this.canvas.parentNode;
                const rect = container.getBoundingClientRect();
                const mouseX = ev.clientX - rect.left;
                const mouseY = ev.clientY - rect.top;
                const ratioX = (mouseX + container.scrollLeft) / this.canvas.width;
                const ratioY = (mouseY + container.scrollTop) / this.canvas.height;
                await (ev.deltaY > 0 ? this.zoomOut() : this.zoomIn());
                container.scrollLeft = ratioX * this.canvas.width - mouseX;
                container.scrollTop = ratioY * this.canvas.height - mouseY;
            },
        },
        _window: {
            "t-on-resize": this.debounced(this.refreshCurrentPage, 500),
        },
        _document: {
            "t-on-fullscreenchange": this.onFullScreenChange,
            "t-on-webkitfullscreenchange": this.onFullScreenChange,
            "t-on-keydown": (ev) => {
                if (ev.target.tagName === "INPUT" || ev.target.tagName === "TEXTAREA") {
                    return;
                }
                if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") {
                    this.changePage(this.currentPage - 1);
                } else if (ev.key === "ArrowRight" || ev.key === "ArrowDown") {
                    this.changePage(this.currentPage + 1);
                }
            },
        },
        "#PDFViewerCanvas": { "t-on-click": this.toggleFullScreenFooter },
        ".oe_slides_share_bar": {
            "t-att-class": () => ({
                "d-none": this.isFullScreen,
            }),
        },
        ".oe_slides_share_bar .oe_slide_js_embed_option_link": {
            "t-on-click.prevent": this.onEmbedShareClick,
        },
        "#page_number": {
            "t-on-change": (ev) => this.changePage(parseInt(ev.currentTarget.value, 10)),
            "t-att-value": () => this.currentPage,
            "t-att-min": () => 1,
            "t-att-max": () => this.pageCount,
        },
        "#zoomout": {
            "t-on-click": this.zoomOut,
            "t-att-class": () => ({ disabled: this.zoom <= this.MIN_ZOOM }),
        },
        "#zoomin": {
            "t-on-click": this.zoomIn,
            "t-att-class": () => ({ disabled: this.zoom >= this.MAX_ZOOM }),
        },
        "#previous": {
            "t-on-click": () => this.changePage(this.currentPage - 1),
            "t-att-class": () => ({ disabled: this.currentPage < 2 && !this.showSuggestions }),
        },
        "#next": {
            "t-on-click": () => this.changePage(this.currentPage + 1),
            "t-att-class": () => ({
                disabled:
                    this.currentPage >= this.pageCount &&
                    (!this.hasSuggestions || this.showSuggestions),
            }),
        },
        "#first": {
            "t-on-click": () => this.changePage(1),
            "t-att-class": () => ({
                disabled: this.currentPage < 2 && !this.showSuggestions,
            }),
        },
        "#last": {
            "t-on-click": () => this.changePage(this.pageCount),
            "t-att-class": () => ({
                disabled: this.currentPage >= this.pageCount,
            }),
        },
        "#fullscreen": { "t-on-click": this.onFullScreenToggleClick },
        "#fullscreen > i": {
            "t-att-class": () => ({
                "fa-arrows-alt": !this.isFullScreen,
                "fa-compress": this.isFullScreen,
            }),
        },
        "#slide_suggest": {
            "t-on-click": (ev) =>
                !ev.target.closest(".oe_slides_suggestion_media") && (this.showSuggestions = false),
            "t-att-class": () => ({
                "d-none": !this.showSuggestions,
            }),
        },
    };

    setup() {
        this.MIN_ZOOM = 1;
        this.MAX_ZOOM = 10;
        this.ZOOM_INCREMENT = 0.5;

        const slideViewer = this.el.querySelector("#PDFSlideViewer");
        this.slideUrl = slideViewer.dataset.slideurl;
        this.canvas = this.el.querySelector("canvas");
        this.canvasContext = this.canvas.getContext("2d");

        this.navBar = this.el.querySelector("#PDFViewerNav");

        this.pdf = null;
        this.renderMutex = new Mutex();
        this.defaultPage = parseInt(slideViewer.dataset.defaultpage, 10);
        this.currentPage = 1;
        this.pageCount = 0;
        this.hasSuggestions = !!this.el.querySelector(".oe_slides_suggestion_media");
        this.showSuggestions = false;

        this.zoom = 1; // 1 = scale to fit
    }

    async willStart() {
        this.pdf = await globalThis.pdfjsLib.getDocument(this.slideUrl).promise;
        if (!this.pdf) {
            return;
        }
        if (this.canvas) {
            this.canvas.style.display = "block";
        }

        this.pageCount = this.pdf.numPages;
        this.el.querySelector("#page_count").textContent = this.pageCount;

        const pageNum =
            1 <= this.defaultPage && this.defaultPage <= this.pageCount ? this.defaultPage : 1;
        await this.renderPage(pageNum);

        this.el.querySelector("#PDFViewerLoader").style.display = "none";
    }

    onEmbedShareClick(ev) {
        this.showSuggestions = false;
        const shareData = ev.currentTarget.dataset;
        this.services.dialog.add(SlideShareDialog, {
            category: shareData.category,
            documentMaxPage: shareData.category === "document" && this.pageCount,
            embedCode: shareData.embedCode || "",
            id: parseInt(shareData.id),
            name: shareData.name,
            url: shareData.url,
        });
    }

    zoomOut() {
        if (this.zoom > this.MIN_ZOOM) {
            this.zoom -= this.ZOOM_INCREMENT;
            return this.refreshCurrentPage();
        }
    }

    zoomIn() {
        if (this.zoom < this.MAX_ZOOM) {
            this.zoom += this.ZOOM_INCREMENT;
            return this.refreshCurrentPage();
        }
    }

    /**
     * Toggle the full screen mode of the PDF viewer. Safari does not support
     * the fullscreen API, so we use the webkit prefix for compatibility.
     */
    onFullScreenToggleClick() {
        if (this.isFullScreen) {
            document.exitFullscreen?.() ?? document.webkitExitFullscreen();
            return;
        }
        this.el.requestFullscreen?.() ?? this.el.webkitRequestFullscreen();
    }

    onFullScreenChange() {
        // By default the navbar is visible in full screen but the user can hide
        // it by clicking on the screen. When exiting full screen we want to
        // make sure the navbar is visible again.
        if (!this.isFullScreen) {
            this.navBar.classList.remove("d-none");
            this.refreshCurrentPage();
        }
    }

    toggleFullScreenFooter() {
        if (this.isFullScreen) {
            this.navBar.classList.toggle("d-none");
            this.refreshCurrentPage();
        }
    }

    get isFullScreen() {
        return !!(document.fullscreenElement || document.webkitFullscreenElement);
    }

    refreshCurrentPage() {
        return this.renderPage(this.currentPage);
    }

    async changePage(pageNumber) {
        this.showSuggestions = false;
        if (1 <= pageNumber && pageNumber <= this.pageCount) {
            await this.renderPage(pageNumber);
        } else if (this.hasSuggestions && pageNumber > this.pageCount) {
            this.showSuggestions = true;
        }
        // We need this because t-att-value updates the attribute in HTML but
        // not the actual value *property* which are decorrelated after the user
        // interacts with the input.
        this.el.querySelector("#page_number").value = this.currentPage;
    }

    /**
     * Get page info from document, resize canvas accordingly, and render page.
     */
    renderPage(pageNumber) {
        return this.renderMutex.exec(async () => {
            this.currentPage = pageNumber;
            const page = await this.pdf.getPage(pageNumber);

            // Each PDF page has its own viewport which defines the size in pixels
            // and initial rotation. We provide the scale at which to render it
            // (relative to the natural size of the document).
            const scale = this.getScaleToFit(page) * this.zoom;
            const viewport = page.getViewport({ scale });

            // Important to match, otherwise the browser will scale the rendered
            // output and it will be ugly.
            this.canvas.height = viewport.height;
            this.canvas.width = viewport.width;
            const renderContext = {
                canvasContext: this.canvasContext,
                viewport: viewport,
            };
            await page.render(renderContext).promise;
        });
    }

    /*
     * Calculate a scale to fit the document on the available space.
     */
    getScaleToFit(page) {
        const parent = this.canvas.parentNode;
        const maxWidth = parent.clientWidth;
        const maxHeight = parent.clientHeight;

        // page.view structure: [x, y, width, height]
        const hScale = maxWidth / page.view[2];
        const vScale = maxHeight / page.view[3];
        return Math.min(hScale, vScale);
    }
}

registry.category("public.interactions").add("website_slides.slides_embed", SlidesEmbed);
