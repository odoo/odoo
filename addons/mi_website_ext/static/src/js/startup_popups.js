/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";

publicWidget.registry.StartupModals = publicWidget.Widget.extend({
  // Usamos el selector correcto para nuestro layout principal
  selector: ".three-column-layout",

  start: function () {
    // Usamos .then() para encadenar nuestra lógica.
    // Esto asegura que se ejecute después de que el widget se haya iniciado.
    return this._super.apply(this, arguments).then(() => {
      this._checkAndShowModals();
    });
  },

  _checkAndShowModals: function () {
    // 2. Usamos 'session.is_public' para comprobar si el usuario es un invitado
    if (session.is_public) {
      return; // No hacer nada para usuarios no logueados
    }

    const termsCookie = "portal_terms_accepted_v1";
    const announcementCookie = "portal_announcements_shown_session";

    if (this._getCookie(announcementCookie)) {
      return;
    }

    if (!this._getCookie(termsCookie)) {
      this._showTermsModal(termsCookie);
    } else {
      this._showAnnouncementsModalIfNeeded();
    }
  },

  _showTermsModal: function (cookieName) {
    const modalElement = this.$("#terms_modal");
    if (modalElement.length) {
      modalElement.modal("show");

      modalElement.find("#accept_terms_btn").one("click", () => {
        this._setCookie(cookieName, "true", 365);
        modalElement.modal("hide");
        // CORRECCIÓN: Llamamos a la función sin parámetros
        this._showAnnouncementsModalIfNeeded();
      });
    }
  },

  _showAnnouncementsModalIfNeeded: function () {
    // El nombre se define aquí dentro

    const announcementCookie = "portal_announcements_shown_session";
    if (this._getCookie(announcementCookie)) {
      return;
    }

    rpc("/get_popup_announcements", {}).then((announcements) => {
      if (!announcements || announcements.length === 0) {
        return;
      }

      const modalElement = this.$("#announcement_popup_modal");
      const listElement = modalElement.find("#popup_announcement_list");

      const confirmButton = modalElement.find("#confirm_all_read_btn");
      listElement.empty();

      announcements.forEach((ann) => {
        const readIcon = ann.is_read
          ? '<i class="fa fa-check-circle text-success me-2"></i>'
          : '<i class="fa fa-circle-o text-muted me-2"></i>';
        const link = `<a href="${ann.website_url || "#"}"
                    class="js_read_tracker ${ann.is_read ? "is-read" : ""}"
                    data-res-model="website.publication"
                    data-res-id="${ann.id}">
                    ${ann.name}
                  </a>`;
        const listItem = `<li class="list-group-item d-flex align-items-center">
                        ${readIcon}
                        ${link}
                      </li>`;
        listElement.append(listItem);
      });

      const allRead = announcements.every((ann) => ann.is_read);

      confirmButton.prop("disabled", !allRead);

      modalElement.modal("show");

      confirmButton.off("click").on("click", () => {
        // Volvemos a comprobar si todo está leído en el momento del clic
        const allCurrentlyRead = announcements.every((ann) => {
          // Buscamos si el `li` correspondiente tiene el check verde
          const announcementLi = listElement
            .find(`a[data-res-id="${ann.id}"]`)
            .parent("li");
          return announcementLi.find(".fa-check-circle").length > 0;
        });

        if (!confirmButton.prop('disabled')) {
          const announcementCookieName = "portal_announcements_shown_session";
          this._setCookie(announcementCookieName, "true");
          modalElement.modal("show");
        } else {
          alert(
            "Aún tienes anuncios pendientes por leer. Por favor, haz clic en cada uno para visualizarlos."
          );
        }
      });

      modalElement.on("hidden.bs.modal", () => {
        rpc("/portal/sidebar/announcements").then((res) => {
          if (res && res.html) {
            const container = document.querySelector(".announcements-section");
            if (container) {
              container.outerHTML = res.html;
            }
          }
        });
      });
    });
  },

  // --- Funciones de Ayuda para Cookies ---
  _getCookie: function (name) {
    const match = document.cookie.match(
      new RegExp("(^| )" + name + "=([^;]+)")
    );
    return match ? match[2] : null;
  },

  _setCookie: function (name, value, days) {
    let expires = "";
    // Si no se especifican días, la cookie será de sesión.
    if (days) {
      const date = new Date();
      date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
      expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
  },
});
