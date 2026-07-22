import { Component, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSubEnv } from "@web/owl2/utils";
import { useSetupAction } from "@web/search/action_hook";
import { Layout } from "@web/search/layout";
import { getDefaultConfig } from "@web/views/view";

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
export class ReportAction extends Component {
    static components = { Layout };
    static template = "web.ReportAction";

    props = useProps({
        display_name: t.string().optional(),
        name: t.string().optional(),
        report_url: t.string(),
        report_name: t.string(),
        data: t.or([t.object(), t.literal(null)]).optional(),
        context: t.object().optional(),
    });

    setup() {
        useSubEnv({
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
        });
        useSetupAction();

        this.action = useService("action");
        this.title = this.props.display_name || this.props.name;
        this.reportUrl = this.props.report_url;
    }

    /**
     * @param {Event & { currentTarget: HTMLIFrameElement }} ev
     */
    onIframeLoaded(ev) {
        const iframeDoc = ev.currentTarget.contentDocument;
        iframeDoc.body.classList.add("o_in_iframe", "container-fluid");
        iframeDoc.body.classList.remove("container");

        // Search the elements with the selector, update them and bind an action.
        for (const element of iframeDoc.querySelectorAll("[res-id][res-model][view-type]")) {
            const wrapper = iframeDoc.createElement("a");
            wrapper.setAttribute("href", "#");
            wrapper.addEventListener("click", (ev) => {
                ev.preventDefault();
                this.action.doAction({
                    type: "ir.actions.act_window",
                    view_mode: element.getAttribute("view-type"),
                    res_id: Number(element.getAttribute("res-id")),
                    res_model: element.getAttribute("res-model"),
                    views: [[element.getAttribute("view-id"), element.getAttribute("view-type")]],
                });
            });
            wrapper.appendChild(element);
            element.parentNode.insertBefore(wrapper, element);
        }
    }

    print() {
        this.action.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: this.props.report_name,
            data: this.props.data || {},
            context: this.props.context || {},
            display_name: this.title,
        });
    }
}
