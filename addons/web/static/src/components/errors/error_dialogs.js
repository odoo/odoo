// @ts-check
/** @odoo-module native */

import { Component, markup, useState } from "@odoo/owl";
import { CopyButton } from "@web/components/copy_button/copy_button";
import { useAction } from "@web/core/action_port";
import { browser } from "@web/core/browser/browser";
import { DateTime } from "@web/core/l10n/luxon";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { capitalize } from "@web/core/utils/format/strings";
import { Dialog } from "@web/ui/dialog/dialog";

/**
 * @typedef {Object} StandardErrorDialogProps
 * @property {string | null} [traceback]
 * @property {string} [message]
 * @property {string} [name]
 * @property {string | null} [exceptionName]
 * @property {Object | null} [data]
 * @property {string | null} [subType]
 * @property {number | string | null} [code]
 * @property {string | null} [type]
 * @property {string | null} [serverHost]
 * @property {number | null} [id]
 * @property {string | null} [model]
 * @property {Function} close
 */

export const standardErrorDialogProps = {
    traceback: { type: [String, { value: null }], optional: true },
    message: { type: String, optional: true },
    name: { type: String, optional: true },
    exceptionName: { type: [String, { value: null }], optional: true },
    data: { type: [Object, { value: null }], optional: true },
    subType: { type: [String, { value: null }], optional: true },
    code: { type: [Number, String, { value: null }], optional: true },
    type: { type: [String, { value: null }], optional: true },
    serverHost: { type: [String, { value: null }], optional: true },
    id: { type: [Number, { value: null }], optional: true },
    model: { type: [String, { value: null }], optional: true },
    close: Function,
};

/**
 * @param {string | null | undefined} exceptionName
 * @returns {string | undefined}
 */
function titleForException(exceptionName) {
    return exceptionName
        ? odooExceptionTitleMap.get(exceptionName)?.toString()
        : undefined;
}

export class ErrorDialog extends Component {
    static template = "web.ErrorDialog";
    static components = { CopyButton, Dialog };
    static title = _t("Odoo Error");
    static showTracebackButtonText = _t("See technical details");
    static hideTracebackButtonText = _t("Hide technical details");
    static props = { ...standardErrorDialogProps };

    setup() {
        this.state = useState({
            showTraceback: false,
        });
        const when = `${DateTime.now()
            .setZone("UTC")
            .toFormat("yyyy-MM-dd HH:mm:ss")} GMT`;
        const { model, serverHost: host } = this.props;
        if (host && model) {
            this.contextDetails = _t(
                "Occurred on %(host)s on model %(model)s on %(when)s",
                { host, model, when },
            );
        } else if (host) {
            this.contextDetails = _t("Occurred on %(host)s on %(when)s", {
                host,
                when,
            });
        } else if (model) {
            this.contextDetails = _t("Occurred on model %(model)s on %(when)s", {
                model,
                when,
            });
        } else {
            this.contextDetails = _t("Occurred on %(when)s", { when });
        }
    }

    /** @returns {string} */
    get title() {
        return /** @type {any} */ (this.constructor).title;
    }

    /** @returns {string | null | undefined} */
    get traceback() {
        return this.props.traceback;
    }

    /** @returns {string} */
    get clipboardReport() {
        return `${this.props.name}\n\n${this.props.message}\n\n${this.contextDetails}\n\n${this.traceback}`;
    }

    /** @returns {string} */
    get copiedText() {
        return _t("Copied");
    }
}

export class ClientErrorDialog extends ErrorDialog {
    static title = _t("Odoo Client Error");
}

export class NetworkErrorDialog extends ErrorDialog {
    static title = _t("Odoo Network Error");
}

export class RequestEntityTooLargeErrorDialog extends ErrorDialog {
    static title = _t("The request sent to the server was too large");
}

export class RPCErrorDialog extends ErrorDialog {
    /** @returns {string} */
    get title() {
        const known = titleForException(this.props.exceptionName);
        if (known) {
            return known;
        }
        switch (this.props.type) {
            case "server":
                return _t("Odoo Server Error");
            case "script":
                return _t("Odoo Client Error");
            case "network":
                return _t("Odoo Network Error");
        }
        return super.title;
    }

    /** @returns {string | null | undefined} */
    get traceback() {
        const debug = this.props.data?.debug;
        if (!debug) {
            return this.props.traceback;
        }
        return `${debug}\nThe above server error caused the following client error:\n${this.props.traceback}`;
    }
}

export class WarningDialog extends Component {
    static template = "web.WarningDialog";
    static components = { Dialog };
    static props = {
        ...standardErrorDialogProps,
        title: { type: String, optional: true },
    };

    setup() {
        this.title = this.inferTitle();
        const { data, message } = this.props;
        if (data?.arguments?.length > 0) {
            this.message = data.arguments[0];
        } else {
            this.message = message;
        }
    }
    /** @returns {string} */
    inferTitle() {
        return (
            titleForException(this.props.exceptionName) ||
            this.props.title ||
            _t("Odoo Warning")
        );
    }
}

export class RedirectWarningDialog extends Component {
    static template = "web.RedirectWarningDialog";
    static components = { Dialog };
    static props = { ...standardErrorDialogProps };

    /** @type {import("@web/core/action_port").ActionPort} */
    actionService;

    setup() {
        this.actionService = useAction();
        const { data, subType } = this.props;
        const [message, actionId, buttonText, additionalContext] =
            data?.arguments || [];
        this.title = capitalize(subType) || _t("Odoo Warning");
        this.message = message;
        this.actionId = actionId;
        this.buttonText = buttonText;
        this.additionalContext = additionalContext;
    }
    async onClick() {
        if (!this.actionId) {
            return this.props.close();
        }
        const options = { forceLeave: true };
        if (this.additionalContext) {
            options.additionalContext = this.additionalContext;
        }
        if (this.actionId.help) {
            this.actionId.help = markup(this.actionId.help);
        }
        await this.actionService.doAction(this.actionId, options);
        this.props.close();
    }
}

export class Error504Dialog extends Component {
    static template = "web.Error504Dialog";
    static components = { Dialog };
    static props = { ...standardErrorDialogProps };
}

export class SessionExpiredDialog extends Component {
    static template = "web.SessionExpiredDialog";
    static components = { Dialog };
    static props = { ...standardErrorDialogProps };

    onClick() {
        browser.location.reload();
    }
}

/** @type {{name: string, title?: any, Dialog?: import("@odoo/owl").ComponentConstructor}[]} */
const ODOO_EXCEPTIONS = [
    {
        name: "odoo.exceptions.AccessDenied",
        title: _t("Access Denied"),
        Dialog: WarningDialog,
    },
    {
        name: "odoo.exceptions.AccessError",
        title: _t("Access Error"),
        Dialog: WarningDialog,
    },
    {
        name: "odoo.exceptions.MissingError",
        title: _t("Missing Record"),
        Dialog: WarningDialog,
    },
    {
        name: "odoo.addons.web.controllers.action.MissingActionError",
        title: _t("Missing Action"),
        Dialog: WarningDialog,
    },
    {
        name: "odoo.addons.base.models.ir_actions_server.ServerActionWithWarningsError",
        title: _t("Invalid Operation"),
        Dialog: WarningDialog,
    },
    {
        name: "odoo.exceptions.UserError",
        title: _t("Invalid Operation"),
        Dialog: WarningDialog,
    },
    {
        name: "odoo.exceptions.ValidationError",
        title: _t("Validation Error"),
        Dialog: WarningDialog,
    },
    {
        name: "werkzeug.exceptions.Forbidden",
        title: _t("Access Denied"),
        Dialog: WarningDialog,
    },
    { name: "odoo.exceptions.RedirectWarning", Dialog: RedirectWarningDialog },
    { name: "odoo.http.SessionExpiredException", Dialog: SessionExpiredDialog },
    { name: "504", Dialog: Error504Dialog },
];

/** @type {Map<string, any>} */
export const odooExceptionTitleMap = new Map(
    ODOO_EXCEPTIONS.filter((entry) => entry.title).map((entry) => [
        entry.name,
        entry.title,
    ]),
);

const errorDialogRegistry = registry.category("error_dialogs");
for (const { name, Dialog } of ODOO_EXCEPTIONS) {
    if (Dialog) {
        errorDialogRegistry.add(name, Dialog);
    }
}
