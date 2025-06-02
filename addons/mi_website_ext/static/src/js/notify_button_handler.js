/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.NotifyButton = publicWidget.Widget.extend({
  selector: ".notify-button",

  events: {
    click: "_onClickNotifyButton",
  },

  _onClickNotifyButton: function () {
    const $modal = $("#notify_absence_modal");
    if (!$modal.length) return;

    $modal.modal("show");

    const $confirmBtn = $modal.find("#confirm_notify_btn");
    $confirmBtn.off("click").one("click", () => {
      rpc("/notify/absence", {})
        .then((result) => {
          if (result?.success) {
            alert(result.message);
            $modal.modal("hide");
          } else if (result?.error) {
            alert("Error: " + result.error);
          } else {
            alert("Error desconocido al enviar la notificación.");
          }
        })
        .catch(() => {
          alert("Error de comunicación con el servidor.");
        });
    });
  },
});
