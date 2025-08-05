/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";

publicWidget.registry.StartupModals = publicWidget.Widget.extend({
  selector: ".three-column-layout",

  /**
   * @override
   */

  start: function () {
    return this._super.apply(this, arguments).then(() => {
      if (!session.is_public) {
        this.$el.on(
          "hidden.bs.modal",
          "#terms_modal",
          this._onTermsModalClosed.bind(this)
        );
        this.$el.on(
          "hidden.bs.modal",
          "#mandatory_policies_modal",
          this._onPoliciesModalClosed.bind(this)
        );
        this.$el.on(
          "hidden.bs.modal",
          "#update_profile_modal",
          this._onProfileModalClosed.bind(this)
        );

        this.$el.on("policy-read", this._onPolicyRead.bind(this));
        this._checkAndShowModals();
      }
    });
  },

  _checkAndShowModals: function () {
    const announcementCookie = "portal_announcements_shown_session";
    if (this._getCookie(announcementCookie)) {
      return;
    }

    rpc("/portal/terms_status", {}).then((res) => {
      if (res && !res.accepted) {
        this._showTermsModal();
      } else {
        this._checkAndShowPoliciesModal();
      }
    });
  },

  _onTermsModalClosed: function () {
    this._checkAndShowPoliciesModal();
  },

  _checkAndShowPoliciesModal: function () {
    rpc("/portal/mandatory_policies_status", {}).then((res) => {
      if (
        res &&
        !res.user_accepted_policies &&
        res.policies &&
        res.policies.length > 0
      ) {
        this._showModal(res.policies, res.read_policy_ids);
      } else {
        this._showProfileUpdateModal();
      }
    });
  },

  _onPoliciesModalClosed: function () {
    this._showProfileUpdateModal();
  },

  _checkProfileUpdate: function () {
    rpc("/portal/profile_update_status", {}).then((res) => {
      if (res.requires_update) {
        this._showProfileUpdateModal();
      } else {
        this._showAnnouncementsModalIfNeeded();
      }
    });
  },

  _onProfileModalClosed: function () {
    this._showAnnouncementsModalIfNeeded();
  },

  //Modal de T&C
  _showTermsModal: function () {
    const modalElement = this.$("#terms_modal");
    if (modalElement.length) {
      const contentElement = modalElement.find("#terms-content");
      const acceptButton = modalElement.find("#accept_terms_btn");

      const checkScroll = () => {
        const tolerance = 5;
        const isAtBottom =
          contentElement.scrollTop() + contentElement.innerHeight() >=
          contentElement[0].scrollHeight - tolerance;
        const noScrollNeeded =
          contentElement[0].scrollHeight <= contentElement[0].clientHeight;

        if (isAtBottom || noScrollNeeded) {
          acceptButton.prop("disabled", false);
          contentElement.off("scroll", checkScroll);
        }
      };

      acceptButton.one("click", () => {
        if (!acceptButton.prop("disabled")) {
          rpc("/portal/accept_terms", {}).then(() => {
            modalElement.modal("hide");
          });
        }
      });

      modalElement.one("shown.bs.modal", () => {
        contentElement.on("scroll", checkScroll);
        checkScroll();
      });

      modalElement.modal("show");
    }
  },

  // Modal de Policies
  _showModal: function (policies, read_policy_ids) {
    this.allPolicies = policies;
    this.readPolicyIds = new Set(read_policy_ids);

    const $modal = $("#mandatory_policies_modal");
    const $list = $modal.find("#mandatory_policies_list");
    this.confirmButton = $modal.find("#confirm_all_policies_btn");

    $list.empty();
    $list.removeClass("list-group list-group-flush").addClass("policy_group");

    this.allPolicies.forEach((policy) => {
      const isRead = this.readPolicyIds.has(policy.id);
      const readIconHtml = isRead
        ? '<i class="fa fa-check-circle text-success me-2"></i>'
        : '<i class="fa fa-circle-o text-muted me-2"></i>';
      const buttonHtml = `
                <button type="button" class="js-view-policy"
                        data-policy-id="${policy.id}"
                        data-policy-name="${policy.name}"
                        data-pdf-url="${policy.url}">
                    <i class="fa fa-eye me-2"></i>
                    <span>Visualizar</span>
                </button>`;

      const listItem = `
                <li class="policy_item">
                    <span>${policy.name}</span>
                    ${buttonHtml}
                </li>`;
      $list.append(listItem);
    });

    this._updateConfirmButtonState();

    this.confirmButton.off("click").on("click", () => {
      rpc("/portal/confirm_all_policies_read", {}).then((res) => {
        if (res.success) {
          $modal.modal("hide");
          $modal.one("hidden.bs.modal", () => {
            this._showProfileUpdateModal();
          });
        } else {
          alert(res.error || "No se pudo confirmar.");
        }
      });
    });
    $modal.modal("show");
  },

  _onPolicyRead: function (ev, data) {
    if (data && data.policyId) {
      this.readPolicyIds.add(data.policyId);
      const $modal = $("#mandatory_policies_modal");
      if ($modal.is(":visible")) {
        const $button = $modal.find(
          `.js-view-policy[data-policy-id=${data.policyId}]`
        );

        if ($button.find(".fa-check").length === 0) {
          $button.prepend('<i class="fa fa-check text-success me-2"></i>');
        }

        this._updateConfirmButtonState();
      }
    }
  },

  _updateConfirmButtonState: function () {
    if (this.allPolicies && this.confirmButton) {
      const allRead = this.allPolicies.length === this.readPolicyIds.size;
      this.confirmButton.prop("disabled", !allRead);
    }
  },

  //Modal de Perfil
  _showProfileUpdateModal: function () {
    const modalElement = $("#update_profile_modal");
    const confirmButton = modalElement.find("#confirm_profile_updated_btn");
    const checkButton = modalElement.find("#profile_update_check_btn");
    const goToProfileLink = modalElement.find("#go_to_profile_btn");

    confirmButton.prop("disabled", true);
    checkButton.prop("disabled", true);
    checkButton.removeClass('btn-success').addClass('btn-info').text('Ya actualicé mis datos');


    goToProfileLink.off("click").on("click", () => {
      localStorage.setItem("openInKioskMode", "true");
      const profileUrl = goToProfileLink.data("profile-url");
      const windowFeatures = 'toolbar=no,location=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=1024,height=768';
      window.open(profileUrl, 'OdooProfileUpdate', windowFeatures);

    });

    checkButton.off("click").on("click", () => {
      confirmButton.prop("disabled", false);
      checkButton.prop("disabled", true)
        .removeClass("btn-info")
        .addClass("btn-success")
        .text("¡Gracias! Ahora puedes continuar.");
    });

    confirmButton.off("click").on("click", () => {
      rpc("/portal/confirm_profile_updated", {}).then((res) => {
        if (res.success) {
          modalElement.modal("hide");
          modalElement.one("hidden.bs.modal", () => {
            this._showAnnouncementsModalIfNeeded();
          });
        } else {
          alert("No se pudo guardar la confirmación. Intente de nuevo.");
        }
      });
    });

    const storageListener = (event) => {
        if (event.key === 'profileSaveClicked' && event.newValue === 'true') {
            console.log("Señal de 'guardado' recibida desde la otra pestaña.");
            checkButton.prop('disabled', false);
            localStorage.removeItem('profileSaveClicked');
           }
    };

    window.addEventListener('storage', storageListener);

    modalElement.one('hidden.bs.modal', () => {
        window.removeEventListener('storage', storageListener);
    });

    modalElement.modal("show");
  },

  _showAnnouncementsModalIfNeeded: function () {
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
        const allCurrentlyRead = announcements.every((ann) => {
          const announcementLi = listElement
            .find(`a[data-res-id="${ann.id}"]`)
            .parent("li");
          return announcementLi.find(".fa-check-circle").length > 0;
        });

        if (!confirmButton.prop("disabled")) {
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

  // Funciones de Cookies
  _getCookie: function (name) {
    const match = document.cookie.match(
      new RegExp("(^| )" + name + "=([^;]+)")
    );
    return match ? match[2] : null;
  },

  _setCookie: function (name, value, days) {
    let expires = "";
    if (days) {
      const date = new Date();
      date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
      expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
  },
});
