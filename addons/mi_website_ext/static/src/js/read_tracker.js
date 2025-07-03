/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.ReadTrackerButton = publicWidget.Widget.extend({
  // El widget se activa en la sección que contiene el botón
  selector: ".read_confirmation_section",
  events: {
    // Escucha el clic solo en los botones con la clase 'js_mark_as_read'
    "click .js_mark_as_read": "_onMarkAsReadClick",
  },

  _onMarkAsReadClick: function (ev) {
    ev.preventDefault();
    const $button = $(ev.currentTarget);
    // Obtenemos los datos del div padre que tiene la clase 'read_confirmation_section'
    const resModel = this.$el.data("res-model");
    const resId = this.$el.data("res-id");

    if ($button.hasClass("disabled") || !resModel || !resId) {
      return; // No hacer nada si ya está deshabilitado o no tiene datos
    }

    $button.prop("disabled", true).text("Registrando...");

    // Usamos la llamada rpc.query que ya sabemos que funciona en tu entorno
    rpc('/portal/mark_as_read', {
      res_model: resModel,
      res_id: resId,
    }).then((result) => {
      if (result.success) {
        // Si el backend confirma, reemplazamos el botón con el mensaje de éxito
        const successMessage = `
                    <div class="alert alert-success" role="alert">
                        <i class="fa fa-check-circle me-2"/>Leído y Entendido. ¡Gracias!
                    </div>`;
        this.$el.html(successMessage);
      } else {
        alert(result.error || "No se pudo registrar la acción.");
        $button.prop("disabled", false).text("Marcar como Leído y Entendido");
      }
    });
  },
});

$(window).on('popstate', function() {
    var $modal = $('#announcement_popup_modal');
    if ($modal.length) {
        if ($modal.hasClass('show')) {
            $modal.modal('hide');
            setTimeout(function() {
                $modal.modal('show');
            }, 200); // Give time to hide before showing again
        } else {
            // If modal is not open, but should be (e.g., user navigated back to a state where it was open), you can decide to show it
            // Optionally, you could check URL or state to decide
        }
    }
});


