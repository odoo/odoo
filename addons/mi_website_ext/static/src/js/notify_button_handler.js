/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc"; // La importación es la misma

publicWidget.registry.NotifyButton = publicWidget.Widget.extend({
  selector: ".notify-button",
  events: {
    click: "_onClickNotify",
  },

  _onClickNotify: function (ev) {
    ev.preventDefault();
    const modalElement = $("#notify_absence_modal");
    modalElement.modal("show");

    modalElement
      .find("#confirm_notify_btn")
      .off("click")
      .one("click", () => {
        const $button = modalElement.find("#confirm_notify_btn");
        $button.prop("disabled", true).text("Enviando...");

        rpc("/notify/absence", {})
          .then(function (result) {
            if (result && result.error) {
              alert("Error: " + result.error);
            } else if (result && result.message) {
              alert(result.message);
              modalElement.modal("hide");
            } else {
              alert(
                "Este feature estara habilitado proximamente."
              );
            }
          })
          .catch(function () {
            alert("Error de comunicación. Por favor, intenta de nuevo.");
          })
          .finally(function () {
            $button
              .prop("disabled", false)
              .text("Confirmar y Enviar Notificación");
          });
      });
  },
});
