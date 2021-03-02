/** @odoo-module **/

import { Dialog } from "../components/dialog/dialog";
import { useService } from "../core/hooks";
import { capitalize } from "../utils/strings";
import { _lt } from "../services/localization";

const { Component, hooks } = owl;
const { useState } = hooks;

const odooExceptionTitleMap = new Map();

odooExceptionTitleMap.set("odoo.exceptions.AccessDenied", _lt("Access Denied"));
odooExceptionTitleMap.set("odoo.exceptions.AccessError", _lt("Access Error"));
odooExceptionTitleMap.set("odoo.exceptions.MissingError", _lt("Missing Record"));
odooExceptionTitleMap.set("odoo.exceptions.UserError", _lt("User Error"));
odooExceptionTitleMap.set("odoo.exceptions.ValidationError", _lt("Validation Error"));

// -----------------------------------------------------------------------------
// Generic Error Dialog
// -----------------------------------------------------------------------------
export class ErrorDialog extends Component {
  constructor() {
    super(...arguments);
    this.title = this.env._t("Odoo Error");
    this.state = useState({
      showTraceback: false,
    });
  }
  onClickClipboard() {
    odoo.browser.navigator.clipboard.writeText(
      `${this.props.name}\n${this.props.message}\n${this.props.traceback}`
    );
  }
}
ErrorDialog.template = "wowl.ErrorDialog";
ErrorDialog.components = { Dialog };


// -----------------------------------------------------------------------------
// Client Error Dialog
// -----------------------------------------------------------------------------
export class ClientErrorDialog extends ErrorDialog {
  constructor() {
    super(...arguments);
    this.title = this.env._t("Odoo Client Error");
  }
}


// -----------------------------------------------------------------------------
// Server Error Dialog
// -----------------------------------------------------------------------------
export class ServerErrorDialog extends ErrorDialog {
  constructor() {
    super(...arguments);
    this.title = this.env._t("Odoo Server Error");
  }
}

// -----------------------------------------------------------------------------
// Network Error Dialog
// -----------------------------------------------------------------------------
export class NetworkErrorDialog extends ErrorDialog {
  constructor() {
    super(...arguments);
    this.title = this.env._t("Odoo Network Error");
  }
}

// -----------------------------------------------------------------------------
// RPC Error Dialog
// -----------------------------------------------------------------------------
export class RPCErrorDialog extends Component {
  constructor() {
    super(...arguments);
    this.title = this.env._t("Odoo Error");
    this.state = useState({
      showTraceback: false,
    });
    this.inferTitle();
    this.traceback = this.props.traceback;
    if (this.props.data && this.props.data.debug) {
      this.traceback = `${this.props.data.debug}`;
    }
  }
  inferTitle() {
    // If the server provides an exception name that we have in a registry.
    if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
      this.title = odooExceptionTitleMap.get(this.props.exceptionName).toString();
      return;
    }
    // Fall back to a name based on the error type.
    if (!this.props.type) return;
    switch (this.props.type) {
      case "server":
        this.title = this.env._t("Odoo Server Error");
        break;
      case "script":
        this.title = this.env._t("Odoo Client Error");
        break;
      case "network":
        this.title = this.env._t("Odoo Network Error");
        break;
    }
  }
  onClickClipboard() {
    odoo.browser.navigator.clipboard.writeText(
      `${this.props.name}\n${this.props.message}\n${this.traceback}`
    );
  }
}
RPCErrorDialog.template = "wowl.ErrorDialog";
RPCErrorDialog.components = { Dialog };

// -----------------------------------------------------------------------------
// Warning Dialog
// -----------------------------------------------------------------------------
export class WarningDialog extends Component {
  constructor() {
    super(...arguments);
    this.title = this.env._t("Odoo Warning");
    this.inferTitle();
    const { data, message } = this.props;
    if (data && data.arguments && data.arguments.length > 0) {
      this.message = data.arguments[0];
    } else {
      this.message = message;
    }
  }
  inferTitle() {
    if (this.props.exceptionName && odooExceptionTitleMap.has(this.props.exceptionName)) {
      this.title = odooExceptionTitleMap.get(this.props.exceptionName).toString();
    }
  }
}
WarningDialog.template = "wowl.WarningDialog";
WarningDialog.components = { Dialog };

// -----------------------------------------------------------------------------
// Redirect Warning Dialog
// -----------------------------------------------------------------------------
export class RedirectWarningDialog extends Component {
  constructor() {
    super(...arguments);
    this.actionService = useService("action");
    const { data, subType } = this.props;
    const [message, actionId, buttonText, additional_context] = data.arguments;
    this.title = capitalize(subType) || this.env._t("Odoo Warning");
    this.message = message;
    this.actionId = actionId;
    this.buttonText = buttonText;
    this.additionalContext = additional_context;
  }
  onClick() {
    this.actionService.doAction(this.actionId, { additionalContext: this.additionalContext });
  }
  onCancel() {
    this.trigger("dialog-closed");
  }
}
RedirectWarningDialog.template = "wowl.RedirectWarningDialog";
RedirectWarningDialog.components = { Dialog };

// -----------------------------------------------------------------------------
// Error 504 Dialog
// -----------------------------------------------------------------------------
export class Error504Dialog extends Component {
  constructor() {
    super(...arguments);
    this.title = this.env._t("Request timeout");
  }
}
Error504Dialog.template = "wowl.Error504Dialog";
Error504Dialog.components = { Dialog };

// -----------------------------------------------------------------------------
// Expired Session Error Dialog
// -----------------------------------------------------------------------------
export class SessionExpiredDialog extends Component {
  constructor() {
    super(...arguments);
    this.title = this.env._t("Odoo Session Expired");
  }
  onClick() {
    odoo.browser.location.reload();
  }
}
SessionExpiredDialog.template = "wowl.SessionExpiredDialog";
SessionExpiredDialog.components = { Dialog };
