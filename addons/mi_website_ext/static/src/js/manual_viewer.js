/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.ManualViewer = publicWidget.Widget.extend({
  selector: ".access-card-manual",
  events: {
    "click #open_manual_btn": "_onOpenManualClick",
  },

  /**
    @override
   */
  start: function () {
    this._super.apply(this, arguments);

    this.$openManualButton = this.$("#open_manual_btn");

    $("#user_manual_modal").on("hide.bs.modal", () => {
      if (this.$openManualButton.length) {
        this.$openManualButton.focus();
      }
    });
  },

  _onOpenManualClick: function (ev) {
    ev.preventDefault();

    const viewerUrl = "/mi_website_ext/static/src/lib/pdfjs/web/viewer.html";
    const pdfFileUrl = "/mi_website_ext/static/pdf/Intranet_manual.pdf";
    const finalUrl = `${viewerUrl}?file=${encodeURIComponent(pdfFileUrl)}`;
    const $modal = $("#user_manual_modal");
    const $iframe = $modal.find("#manual_pdf_iframe");

    if ($iframe.attr("src") !== finalUrl) {
      $iframe.attr("src", finalUrl);
    }

    $iframe.off("load").on("load", function () {
      try {
        const iframeDocument = $iframe.contents();
        const $printButton = iframeDocument.find("#printButton");
        const $downloadButton = iframeDocument.find("#downloadButton");
        const $editorStampButton = iframeDocument.find("#editorStampButton");
        const $editorInkButton = iframeDocument.find("#editorInkButton");
        const $editorFreeTextButton = iframeDocument.find("#editorFreeTextButton");
        const $editorHighlightButton = iframeDocument.find("#editorHighlightButton");
        $printButton.hide();
        $downloadButton.hide();
        $editorStampButton.hide();
        $editorInkButton.hide();
        $editorFreeTextButton.hide();
        $editorHighlightButton.hide();
        iframeDocument.find("#secondaryToolbarToggle").hide();
      } catch (e) {
        console.error("Error al intentar modificar el iframe de PDF.js:", e);
      }
    });

    $modal.modal("show");
  },
});
