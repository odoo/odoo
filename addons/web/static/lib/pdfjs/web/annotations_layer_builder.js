/* -*- Mode: Java; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set shiftwidth=2 tabstop=2 autoindent cindent expandtab: */
/* Copyright 2014 Mozilla Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
/*globals PDFJS, CustomStyle, mozL10n */

'use strict';

/**
 * @typedef {Object} AnnotationsLayerBuilderOptions
 * @property {HTMLDivElement} pageDiv
 * @property {PDFPage} pdfPage
 * @property {IPDFLinkService} linkService
 */

/**
 * @class
 */
var AnnotationsLayerBuilder = (function AnnotationsLayerBuilderClosure() {
  /**
   * @param {AnnotationsLayerBuilderOptions} options
   * @constructs AnnotationsLayerBuilder
   */
  function AnnotationsLayerBuilder(options) {
    this.pageDiv = options.pageDiv;
    this.pdfPage = options.pdfPage;
    this.linkService = options.linkService;

    this.div = null;
  }
  AnnotationsLayerBuilder.prototype =
      /** @lends AnnotationsLayerBuilder.prototype */ {

    /**
     * @param {PageViewport} viewport
     */
    setupAnnotations:
        function AnnotationsLayerBuilder_setupAnnotations(viewport) {
      function bindLink(link, dest) {
        link.href = linkService.getDestinationHash(dest);
        link.onclick = function annotationsLayerBuilderLinksOnclick() {
          if (dest) {
            linkService.navigateTo(dest);
          }
          return false;
        };
        if (dest) {
          link.className = 'internalLink';
        }
      }

      function bindNamedAction(link, action) {
        link.href = linkService.getAnchorUrl('');
        link.onclick = function annotationsLayerBuilderNamedActionOnClick() {
          linkService.executeNamedAction(action);
          return false;
        };
        link.className = 'internalLink';
      }

      var linkService = this.linkService;
      var pdfPage = this.pdfPage;
      var self = this;

      pdfPage.getAnnotations().then(function (annotationsData) {
        viewport = viewport.clone({ dontFlip: true });
        var transform = viewport.transform;
        var transformStr = 'matrix(' + transform.join(',') + ')';
        var data, element, i, ii;

        if (self.div) {
          // If an annotationLayer already exists, refresh its children's
          // transformation matrices
          for (i = 0, ii = annotationsData.length; i < ii; i++) {
            data = annotationsData[i];
            element = self.div.querySelector(
                '[data-annotation-id="' + data.id + '"]');
            if (element) {
              CustomStyle.setProp('transform', element, transformStr);
            }
          }
          // See PDFPageView.reset()
          self.div.removeAttribute('hidden');
        } else {
          for (i = 0, ii = annotationsData.length; i < ii; i++) {
            data = annotationsData[i];
            if (!data || !data.hasHtml) {
              continue;
            }

            element = PDFJS.AnnotationUtils.getHtmlElement(data,
              pdfPage.commonObjs);
            element.setAttribute('data-annotation-id', data.id);
            if (typeof mozL10n !== 'undefined') {
              mozL10n.translate(element);
            }

            var rect = data.rect;
            var view = pdfPage.view;
            rect = PDFJS.Util.normalizeRect([
              rect[0],
                view[3] - rect[1] + view[1],
              rect[2],
                view[3] - rect[3] + view[1]
            ]);
            element.style.left = rect[0] + 'px';
            element.style.top = rect[1] + 'px';
            element.style.position = 'absolute';

            CustomStyle.setProp('transform', element, transformStr);
            var transformOriginStr = -rect[0] + 'px ' + -rect[1] + 'px';
            CustomStyle.setProp('transformOrigin', element, transformOriginStr);

            if (data.subtype === 'Link' && !data.url) {
              var link = element.getElementsByTagName('a')[0];
              if (link) {
                if (data.action) {
                  bindNamedAction(link, data.action);
                } else {
                  bindLink(link, ('dest' in data) ? data.dest : null);
                }
              }
            }

            if (!self.div) {
              var annotationLayerDiv = document.createElement('div');
              annotationLayerDiv.className = 'annotationLayer';
              self.pageDiv.appendChild(annotationLayerDiv);
              self.div = annotationLayerDiv;
            }

            self.div.appendChild(element);
          }
        }
      });
    },

    hide: function () {
      if (!this.div) {
        return;
      }
      this.div.setAttribute('hidden', 'true');
    }
  };
  return AnnotationsLayerBuilder;
})();

/**
 * @constructor
 * @implements IPDFAnnotationsLayerFactory
 */
function DefaultAnnotationsLayerFactory() {}
DefaultAnnotationsLayerFactory.prototype = {
  /**
   * @param {HTMLDivElement} pageDiv
   * @param {PDFPage} pdfPage
   * @returns {AnnotationsLayerBuilder}
   */
  createAnnotationsLayerBuilder: function (pageDiv, pdfPage) {
    return new AnnotationsLayerBuilder({
      pageDiv: pageDiv,
      pdfPage: pdfPage
    });
  }
};
