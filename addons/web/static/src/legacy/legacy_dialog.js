/** @odoo-module **/

import { Dialog } from "../components/dialog/dialog";
import { patch } from "@web/utils/patch";
import OwlDialog from "web.OwlDialog";

const { hooks } = owl;
const { onMounted, onWillUnmount } = hooks;

/**
 * This is a patch of the new Dialog class.
 * Its purpose is to inform the old "active/inactive" mechanism.
 */
patch(Dialog.prototype, "Legacy Adapted Dialog", {
  setup() {
    this._super();
    onMounted(() => {
      OwlDialog.display(this);
    });
    onWillUnmount(() => {
      OwlDialog.hide(this);
    });
  }
});
