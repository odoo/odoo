/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.PolicyViewer = publicWidget.Widget.extend({
  selector: ".policy_section",
  events: {
    "click .js-view-policy": "_onViewPolicyClick",
  },

  start: function () {
    this._super.apply(this, arguments);
    this.currentPolicyId = null;
    this.currentButtonPlaceholder = null;
    this.messageHandler = this._onWindowMessage.bind(this);
    window.addEventListener("message", this.messageHandler);

    $("#pdf_viewer_modal").on("hidden.bs.modal", () => {
      this.currentPolicyId = null;
      this.currentButtonPlaceholder = null;
    });
  },

  destroy: function () {
    window.removeEventListener("message", this.messageHandler);
    this._super.apply(this, arguments);
  },

  _onWindowMessage: function (ev) {
    if (
      ev.data === "pdf-scrolled-to-end" &&
      this.currentPolicyId &&
      this.currentButtonPlaceholder
    ) {
      const $modal = this.currentButtonPlaceholder.closest(".modal");
      const $headerCloseButton = $modal.find(".btn-close");
      $headerCloseButton.prop("disabled", false);
      const markReadButton = $(
        '<button class="accept-button js_mark_as_read_in_modal">Marcar como Leído</button>'
      );
      this.currentButtonPlaceholder.html(markReadButton);

      markReadButton.one("click", () => {
        this._markPolicyAsRead();
      });
    }
  },

  _onViewPolicyClick: function (ev) {
    ev.preventDefault();
    const $button = $(ev.currentTarget);
    const policyId = $button.data("policy-id");
    const policyName = $button.data("policy-name");
    const pdfUrl = $button.data("pdf-url");
    const viewerBaseUrl =
      "/mi_website_ext/static/src/lib/pdfjs/web/viewer.html";
    const encodedPdfUrl = encodeURIComponent(pdfUrl);

    const modalElement = $("#pdf_viewer_modal");
    const $iframe = modalElement.find("iframe");
    modalElement.find("#pdf_modal_title").text(policyName);
    $iframe.attr(
      "src",
      `${viewerBaseUrl}?file=${encodedPdfUrl}&policy_id=${policyId}`
    );

    $iframe.off("load").on("load", function () {
      try {
        const iframeDocument = $iframe.contents();
        const $printButton = iframeDocument.find("#printButton");
        const $downloadButton = iframeDocument.find("#downloadButton");
        const $editorStampButton = iframeDocument.find("#editorStampButton");
        const $editorInkButton = iframeDocument.find("#editorInkButton");
        const $editorFreeTextButton = iframeDocument.find(
          "#editorFreeTextButton"
        );
        const $editorHighlightButton = iframeDocument.find(
          "#editorHighlightButton"
        );
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

    const $headerCloseButton = modalElement.find(".btn-close");
    $headerCloseButton.prop("disabled", true);

    const readButtonPlaceholder = modalElement.find(
      "#pdf_modal_read_button_placeholder"
    );

    const alreadyRead = $button.find(".fa-check").length > 0;

    if (alreadyRead) {
      $headerCloseButton.prop("disabled", false);
      readButtonPlaceholder.html(`
                <div class="alert alert-success m-0 p-2">
                    <i class="fa fa-check-circle me-2"/>Leído y Entendido
                </div>`);
    } else {
      readButtonPlaceholder.empty();
      this.currentPolicyId = policyId;
      this.currentButtonPlaceholder = readButtonPlaceholder;
    }

    modalElement.modal("show");
  },

  _markPolicyAsRead: function () {
    const policyId = this.currentPolicyId;
    const buttonPlaceholder = this.currentButtonPlaceholder;
    if (!policyId || !buttonPlaceholder) {
      return;
    }
    buttonPlaceholder
      .find("button")
      .prop("disabled", true)
      .text("Registrando...");

    rpc("/portal/mark_as_read", {
      res_model: "website.publication",
      res_id: policyId,
    }).then((result) => {
      if (result.success) {
        const successMessage = `
                        <div class="alert alert-success m-0 p-2">
                            <i class="fa fa-check-circle me-2"/>Registrado. ¡Gracias!
                        </div>`;
        buttonPlaceholder.html(successMessage);
        $(`.js-view-policy[data-policy-id=${policyId}]`).prepend(
          '<i class="fa fa-check text-success me-2"/>'
        );
        this.currentPolicyId = null;
        $(".three-column-layout").trigger("policy-read", {
          policyId: policyId,
        });
      } else {
        alert(result.error || "No se pudo registrar la acción.");
        buttonPlaceholder
          .find("button")
          .prop("disabled", false)
          .text("Marcar como Leído");
      }
    });
  },
});
