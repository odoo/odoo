/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.PolicyViewer = publicWidget.Widget.extend({
  selector: ".policy_section",
  events: {
    "click .js-view-policy": "_onViewPolicyClick",
  },

  /**
   * Se añade el método start para inicializar el listener de mensajes.
   * Este se ejecutará una vez cuando el widget se cargue en la página.
   */
  start: function () {
    this._super.apply(this, arguments);
    this.currentPolicyId = null;
    this.currentButtonPlaceholder = null;
    this.messageHandler = this._onWindowMessage.bind(this);
    window.addEventListener("message", this.messageHandler);

    // Es una buena práctica limpiar el estado cuando el modal se cierra
    $("#pdf_viewer_modal").on("hidden.bs.modal", () => {
      this.currentPolicyId = null;
      this.currentButtonPlaceholder = null;
    });
  },

  /**
   * Se añade el método destroy para limpiar el listener cuando se destruye el widget.
   */
  destroy: function () {
    window.removeEventListener("message", this.messageHandler);
    this._super.apply(this, arguments);
  },

  /**
   * NUEVO: Este método escucha los mensajes del iframe.
   * Cuando recibe la señal 'pdf-scrolled-to-end', crea el botón.
   */
  _onWindowMessage: function (ev) {
    if (
      ev.data === "pdf-scrolled-to-end" &&
      this.currentPolicyId &&
      this.currentButtonPlaceholder
    ) {
      const $modal = this.currentButtonPlaceholder.closest('.modal');
      const $headerCloseButton = $modal.find('.btn-close');
      $headerCloseButton.prop('disabled', false);
      const markReadButton = $(
        '<button class="btn btn-primary js_mark_as_read_in_modal">Marcar como Leído</button>'
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

    modalElement.find("#pdf_modal_title").text(policyName);
    // Aseguramos que la URL del iframe se actualice cada vez que se abre el modal
    modalElement
      .find("iframe")
      .attr(
        "src",
        `${viewerBaseUrl}?file=${encodedPdfUrl}&policy_id=${policyId}`
      );

    const $headerCloseButton = modalElement.find('.btn-close');
    $headerCloseButton.prop('disabled', true);

    const readButtonPlaceholder = modalElement.find(
      "#pdf_modal_read_button_placeholder"
    );

    const alreadyRead = $button.find(".fa-check").length > 0;

    if (alreadyRead) {
      // Tu lógica para políticas ya leídas (esta parte no cambia, es correcta)
      $headerCloseButton.prop('disabled', false);
      readButtonPlaceholder.html(`
                <div class="alert alert-success m-0 p-2">
                    <i class="fa fa-check-circle me-2"/>Leído y Entendido
                </div>`);
    } else {
      // --- CAMBIO PRINCIPAL AQUÍ ---
      // Si la política NO ha sido leída, en lugar de crear el botón,
      // simplemente vaciamos el contenedor y guardamos el contexto.
      // El método _onWindowMessage se encargará de crear el botón más tarde.
      readButtonPlaceholder.empty(); // Limpiamos cualquier botón o mensaje anterior
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
    // Tu lógica de RPC no necesita cambios, es correcta.
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
