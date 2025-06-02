/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.PolicyViewer = publicWidget.Widget.extend({
  selector: ".policy_section", // El widget se activa en la sección que contiene los botones
  events: {
    "click .js-view-policy": "_onViewPolicyClick",
  },

  _onViewPolicyClick: function (ev) {
    ev.preventDefault();
    const $button = $(ev.currentTarget);
    const policyId = $button.data("policy-id");
    const policyName = $button.data("policy-name");
    const pdfUrl = $button.data("pdf-url");

    const modalElement = $("#pdf_viewer_modal");

    // 1. Preparamos el modal antes de mostrarlo
    modalElement.find("#pdf_modal_title").text(policyName);
    modalElement.find("#pdf_embed_container").attr("src", pdfUrl);

    // 2. Preparamos el botón de "Marcar como Leído"
    const readButtonPlaceholder = modalElement.find(
      "#pdf_modal_read_button_placeholder"
    );

    // Verificamos si ya está leído (basado en el check de la lista)
    const alreadyRead = $button.find(".fa-check").length > 0;

    if (alreadyRead) {
      readButtonPlaceholder.html(`
                <div class="alert alert-success m-0 p-2">
                    <i class="fa fa-check-circle me-2"/>Leído y Entendido
                </div>`);
    } else {
      const markReadButton = $(
        '<button class="btn btn-primary js_mark_as_read_in_modal">Marcar como Leído</button>'
      );
      readButtonPlaceholder.html(markReadButton);

      markReadButton.one("click", () => {
        this._markPolicyAsRead(policyId, readButtonPlaceholder);
      });
    }

    // 3. Mostramos el modal
    modalElement.modal("show");
  },

  _markPolicyAsRead: function (policyId, buttonPlaceholder) {
    // Deshabilitamos el botón para evitar dobles clics
    buttonPlaceholder
      .find("button")
      .prop("disabled", true)
      .text("Registrando...");

    rpc("/portal/mark_as_read", {
      res_model: "website.publication", // Usamos el modelo unificado
      res_id: policyId,
    }).then((result) => {
      if (result.success) {
        // Reemplazamos el botón con el mensaje de éxito
        const successMessage = `
                    <div class="alert alert-success m-0 p-2">
                        <i class="fa fa-check-circle me-2"/>Registrado. ¡Gracias!
                    </div>`;
        buttonPlaceholder.html(successMessage);
        // Actualizamos también el botón en la lista principal
        $(`.js-view-policy[data-policy-id=${policyId}]`).prepend(
          '<i class="fa fa-check text-success me-2"/>'
        );
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
