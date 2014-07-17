/**
 * @license
 * Copyright (C) 2013 KO GmbH <copyright@kogmbh.com>
 *
 * @licstart
 * The JavaScript code in this page is free software: you can redistribute it
 * and/or modify it under the terms of the GNU Affero General Public License
 * (GNU AGPL) as published by the Free Software Foundation, either version 3 of
 * the License, or (at your option) any later version.  The code is distributed
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU AGPL for more details.
 *
 * As additional permission under GNU AGPL version 3 section 7, you
 * may distribute non-source (e.g., minimized or compacted) forms of
 * that code without the copy of the GNU GPL normally required by
 * section 4, provided you include this license notice and a URL
 * through which recipients can access the Corresponding Source.
 *
 * As a special exception to the AGPL, any HTML file which merely makes function
 * calls to this code, and for that purpose includes it by reference shall be
 * deemed a separate work for copyright law purposes. In addition, the copyright
 * holders of this code give you permission to combine this code with free
 * software libraries that are released under the GNU LGPL. You may copy and
 * distribute such a system following the terms of the GNU AGPL for this code
 * and the LGPL for the libraries. If you modify this code, you may extend this
 * exception to your version of the code, but you are not obligated to do so.
 * If you do not wish to do so, delete this exception statement from your
 * version.
 *
 * This license applies to this entire compilation.
 * @licend
 * @source: http://viewerjs.org/
 * @source: http://github.com/kogmbh/Viewer.js
 */

/*global document, PDFJS, console, TextLayerBuilder*/


function PDFViewerPlugin() {
    "use strict";

    function init(callback) {
        var pdfLib, textLayerLib, pluginCSS;

        pdfLib = document.createElement('script');
        pdfLib.async = false;
        pdfLib.src = './pdf.js';
        pdfLib.type = 'text/javascript';
        pdfLib.onload = function () {
            textLayerLib = document.createElement('script');
            textLayerLib.async = false;
            textLayerLib.src = './TextLayerBuilder.js';
            textLayerLib.type = 'text/javascript';
            textLayerLib.onload = callback;
            document.getElementsByTagName('head')[0].appendChild(textLayerLib);
        };
        document.getElementsByTagName('head')[0].appendChild(pdfLib);

        pluginCSS = document.createElement('link');
        pluginCSS.setAttribute("rel", "stylesheet");
        pluginCSS.setAttribute("type", "text/css");
        pluginCSS.setAttribute("href", "./PDFViewerPlugin.css");
        document.head.appendChild(pluginCSS);
    }

    var self = this,
        pages = [],
        domPages = [],
        pageText = [],
        renderingStates = [],
        RENDERING = {
            BLANK: 0,
            RUNNING: 1,
            FINISHED: 2
        },
        startedTextExtraction = false,
        container = null,
        initialized = false,
        pdfDocument = null,
        pageViewScroll = null,
        isPresentationMode = false,
        scale = 1,
        currentPage = 1,
        pageWidth,
        pageHeight,
        createdPageCount = 0;

    function scrollIntoView(elem) {
        elem.parentNode.scrollTop = elem.offsetTop;
    }

    function isScrolledIntoView(elem) {
        var docViewTop = container.scrollTop,
            docViewBottom = docViewTop + container.clientHeight,
            elemTop = elem.offsetTop,
            elemBottom = elemTop + elem.clientHeight;

        // Is in view if either the top or the bottom of the page is between the
        // document viewport bounds,
        // or if the top is above the viewport and the bottom is below it.
        return (elemTop >= docViewTop && elemTop < docViewBottom)
                || (elemBottom >= docViewTop && elemBottom < docViewBottom)
                || (elemTop < docViewTop && elemBottom >= docViewBottom);
    }

    function getDomPage(page) {
        return domPages[page.pageInfo.pageIndex];
    }
    function getPageText(page) {
        return pageText[page.pageInfo.pageIndex];
    }
    function getRenderingStatus(page) {
        return renderingStates[page.pageInfo.pageIndex];
    }
    function setRenderingStatus(page, renderStatus) {
        renderingStates[page.pageInfo.pageIndex] = renderStatus;
    }

    function updatePageDimensions(page, width, height) {
        var domPage = getDomPage(page),
            canvas = domPage.getElementsByTagName('canvas')[0],
            textLayer = domPage.getElementsByTagName('div')[0];

        domPage.style.width = width;
        domPage.style.height = height;

        canvas.width = width;
        canvas.height = height;

        textLayer.style.width = width;
        textLayer.style.height = height;

        // Once the page dimension is updated, the rendering state is blank.
        setRenderingStatus(page, RENDERING.BLANK);
    }

    function renderPage(page) {
        var domPage = getDomPage(page),
            textLayer = getPageText(page),
            canvas = domPage.getElementsByTagName('canvas')[0];

        if (getRenderingStatus(page) === RENDERING.BLANK) {
            setRenderingStatus(page, RENDERING.RUNNING);
            page.render({
                canvasContext: canvas.getContext('2d'),
                textLayer: textLayer,
                viewport: page.getViewport(scale)
            }).then(function () {
                setRenderingStatus(page, RENDERING.FINISHED);
            });
        }
    }

    function createPage(page) {
        var pageNumber,
            textLayerDiv,
            textLayer,
            canvas,
            domPage,
            viewport;

        pageNumber = page.pageInfo.pageIndex + 1;

        viewport = page.getViewport(scale);

        domPage = document.createElement('div');
        domPage.id = 'pageContainer' + pageNumber;
        domPage.className = 'page';

        canvas = document.createElement('canvas');
        canvas.id = 'canvas' + pageNumber;

        textLayerDiv = document.createElement('div');
        textLayerDiv.className = 'textLayer';
        textLayerDiv.id = 'textLayer' + pageNumber;

        container.appendChild(domPage);
        domPage.appendChild(canvas);
        domPage.appendChild(textLayerDiv);

        pages.push(page);
        domPages.push(domPage);
        renderingStates.push(RENDERING.BLANK);

        updatePageDimensions(page, viewport.width, viewport.height);
        pageWidth = viewport.width;
        pageHeight = viewport.height;

        textLayer = new TextLayerBuilder({
            textLayerDiv: textLayerDiv,
            pageIndex: pageNumber - 1
        });
        page.getTextContent().then(function (textContent) {
            textLayer.setTextContent(textContent);
        });
        pageText.push(textLayer);

        createdPageCount += 1;
        if (createdPageCount === (pdfDocument.numPages)) {
            self.onLoad();
        }
    }

    this.initialize = function (viewContainer, location) {
        var self = this,
            i,
            pluginCSS;

        init(function () {
            PDFJS.workerSrc = "./pdf.worker.js";
            PDFJS.getDocument(location).then(function loadPDF(doc) {
                pdfDocument = doc;
                container = viewContainer;

                for (i = 0; i < pdfDocument.numPages; i += 1) {
                    pdfDocument.getPage(i + 1).then(createPage);
                }

                initialized = true;
            });
        });
    };

    this.isSlideshow = function () {
        // A very simple but generally true guess - if the width is greater than the height, treat it as a slideshow
        return pageWidth > pageHeight;
    };

    this.onLoad = function () {};

    this.getPages = function () {
        return domPages;
    };

    this.getWidth = function () {
        return pageWidth;
    };

    this.getHeight = function () {
        return pageHeight;
    };

    this.fitToWidth = function (width) {
        var zoomLevel;

        if (self.getWidth() === width) {
            return;
        }
        zoomLevel = width / pageWidth;
        self.setZoomLevel(zoomLevel);
    };

    this.fitToHeight = function (height) {
        var zoomLevel;

        if (self.getHeight() === height) {
            return;
        }
        zoomLevel = height / pageHeight;
        self.setZoomLevel(zoomLevel);
    };

    this.fitToPage = function (width, height) {
        var zoomLevel = width / pageWidth;
        if (height / pageHeight < zoomLevel) {
            zoomLevel = height / pageHeight;
        }
        self.setZoomLevel(zoomLevel);
    };

    this.fitSmart = function (width, height) {
        var zoomLevel = width / pageWidth;
        if (height && (height / pageHeight) < zoomLevel) {
            zoomLevel = height / pageHeight;
        }
        zoomLevel = Math.min(1.0, zoomLevel);
        self.setZoomLevel(zoomLevel);
    };

    this.setZoomLevel = function (zoomLevel) {
        var i;

        if (scale !== zoomLevel) {
            scale = zoomLevel;

            for (i = 0; i < pages.length; i += 1) {
                updatePageDimensions(pages[i], pageWidth * scale, pageHeight * scale);
            }
        }
    };

    this.getZoomLevel = function () {
        return scale;
    };

    this.onScroll = function () {
        var i;

        for (i = 0; i < domPages.length; i += 1) {
            if (isScrolledIntoView(domPages[i])) {
                if (getRenderingStatus(pages[i]) === RENDERING.BLANK) {
                    renderPage(pages[i]);
                }
            }
        }
    };

    this.getPageInView = function () {
        var i;
        for (i = 0; i < domPages.length; i += 1) {
            if (isScrolledIntoView(domPages[i])) {
                return i + 1;
            }
        }
    };

    this.showPage = function (n) {
        scrollIntoView(domPages[n - 1]);
    };
}
