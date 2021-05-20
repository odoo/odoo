/** @odoo-module alias=report.client_action **/

// GES: FIXME
// Remove legacy imports to CP
import ControlPanel from "web.ControlPanel";
import { breadcrumbsToLegacy } from "@web/legacy/backend_utils";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useEnrichWithActionLinks } from "@web/webclient/actions/ux_hooks";
const { Component, hooks } = owl;

/**
 * Most of the time reports are printed as pdfs.
 * However, reports have 3 possible actions: pdf, text and HTML.
 * This file is the HTML action.
 * The HTML action is a client action (with control panel) rendering the template in an iframe.
 * If not defined as the default action, the HTML is the fallback to pdf if wkhtmltopdf is not available.
 *
 * It has a button to print the report.
 * It uses a feature to automatically create links to other odoo pages if the selector [res-id][res-model][view-type]
 * is detected.
 */
export default class ReportClientAction extends Component {
    setup() {
        this.actionService = useService("action");
        this.title = this.props.display_name || this.props.name;
        this.report_url = this.props.report_url;
        this.iframe = hooks.useRef("iframe");
        useEnrichWithActionLinks(this.iframe);
    }

    onIframeLoaded(ev) {
        const iframeDocument = ev.target.contentWindow.document;
        iframeDocument.body.classList.add("o_in_iframe", "container-fluid");
        iframeDocument.body.classList.remove("container");
    }

    breadcrumbClicked(ev) {
        // GES: FIXME
        // waiting for DAM Control Panel
        this.actionService.restore(ev.detail.controllerID);
    }

    get breadcrumbs() {
        // GES: FIXME
        // waiting for DAM Control Panel
        return breadcrumbsToLegacy(this.props.breadcrumbs);
    }

    print() {
        this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: this.props.options.report_name,
            report_file: this.props.options.report_file,
            data: this.props.options.data || {},
            context: this.props.options.context || {},
            display_name: this.title,
        });
    }
}
ReportClientAction.components = { ControlPanel };
ReportClientAction.template = "web.ReportClientAction";

registry.category("actions").add("report.client_action", ReportClientAction);
