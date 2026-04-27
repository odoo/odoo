import { Component, useRef } from "@odoo/owl";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { useViewCompiler } from "@web/views/view_compiler";
import { GanttCompiler } from "./gantt_compiler";

export class GanttPopover extends Component {
    static template = "web_gantt.GanttPopover";
    static components = { ViewButton };
    static props = [
        "title",
        "displayGenericButtons",
        "bodyTemplate?",
        "footerTemplate?",
        "resModel",
        "resId",
        "context",
        "close",
        "reload",
        "buttons",
    ];

    setup() {
        this.rootRef = useRef("root");

        this.templates = { body: "web_gantt.GanttPopover.default" };
        const toCompile = {};
        const { bodyTemplate, footerTemplate } = this.props;
        if (bodyTemplate) {
            toCompile.body = bodyTemplate;
            if (footerTemplate) {
                toCompile.footer = footerTemplate;
            }
        }
        Object.assign(
            this.templates,
            useViewCompiler(GanttCompiler, toCompile, { recordExpr: "__record__" })
        );

        useViewButtons(this.rootRef, {
            reload: async () => {
                await this.props.reload();
                this.props.close();
            },
        });
    }

    get renderingContext() {
        return Object.assign({}, this.props.context, {
            __comp__: this,
            __record__: { resModel: this.props.resModel, resId: this.props.resId },
        });
    }

    async onClick(button) {
        await button.onClick();
        this.props.close();
    }
}
