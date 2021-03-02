/** @odoo-module **/

const { Component, hooks, misc } = owl;
const { useRef, useExternalListener, useSubEnv } = hooks;
const { Portal } = misc;

export class Dialog extends Component {
  constructor(parent, props) {
    super(...arguments);
    this.modalRef = useRef("modal");
    useExternalListener(window, "keydown", this._onKeydown);
    useSubEnv({ inDialog: true });
  }

  mounted() {
    const dialogContainer = document.querySelector(".o_dialog_container");
    const modals = dialogContainer.querySelectorAll(".o_dialog .modal");
    const len = modals.length;
    for (let i = 0; i < len - 1; i++) {
      const modal = modals[i];
      modal.classList.add("o_inactive_modal");
    }
    dialogContainer.classList.add("modal-open");
  }

  willUnmount() {
    const dialogContainer = document.querySelector(".o_dialog_container");
    const modals = dialogContainer.querySelectorAll(".o_dialog .modal");
    const len = modals.length;
    if (len >= 2) {
      const modal = this.modalRef.el === modals[len - 1] ? modals[len - 2] : modals[len - 1];
      modal.focus();
      modal.classList.remove("o_inactive_modal");
    } else {
      dialogContainer.classList.remove("modal-open");
    }
  }

  /**
   * Send an event signaling that the dialog should be closed.
   * @private
   */
  _close() {
    this.trigger("dialog-closed");
  }

  /**
   *
   * @param {KeyboardEvent} ev
   */
  _onKeydown(ev) {
    var _a;
    if (
      ev.key === "Escape" &&
      !((_a = this.modalRef.el) === null || _a === void 0
        ? void 0
        : _a.classList.contains("o_inactive_modal"))
    ) {
      this._close();
    }
  }
}

Dialog.components = { Portal };
Dialog.props = {
  contentClass: { type: String, optional: true },
  fullscreen: Boolean,
  renderFooter: Boolean,
  renderHeader: Boolean,
  size: {
    type: String,
    validate: (s) => ["modal-xl", "modal-lg", "modal-md", "modal-sm"].includes(s),
  },
  technical: Boolean,
  title: String,
};
Dialog.defaultProps = {
  fullscreen: false,
  renderFooter: true,
  renderHeader: true,
  size: "modal-lg",
  technical: true,
  title: "Odoo",
};
Dialog.template = "wowl.Dialog";
