import { Component, signal, t, useProps } from "@odoo/owl";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { getBasicEvalContext } from "@web/model/relational_model/utils";
import { HelpCompiler } from "@web/views/help/help_compiler";
import { HelpWidget } from "@web/views/help/help_widget";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { useViewCompiler } from "@web/views/view_compiler";

/**
 * Renders a help view (see `help_id` view attribute), with the given data.
 */
export class HelpRenderer extends Component {
    static template = "web.HelpRenderer";
    static components = { HelpWidget, ViewButton };
    props = useProps({
        archInfo: t.object(),
        actionHelp: t.string(),
        data: t.object(),
    });

    rootRef = signal.ref();

    setup() {
        this.helpArchInfo = this.props.archInfo;
        const templates = useViewCompiler(
            HelpCompiler,
            { help: this.helpArchInfo.xmlDoc },
            { recordExpr: "__comp__.helpRecord" }
        );
        this.helpTemplate = templates.help;
        this.evaluateBooleanExpr = evaluateBooleanExpr;

        useViewButtons(this.rootRef, { reload: () => this.env.searchModel.search() });
    }

    /**
     * Fake "record" given to the ViewButtons of the help, and used to evaluate
     * `invisible` attributes: there is no record, only the action context and
     * the data of the help.
     */
    get helpRecord() {
        const context = this.env.searchModel.context;
        const evalContext = { ...getBasicEvalContext({ context }), data: this.props.data };
        return {
            context,
            evalContext,
            evalContextWithVirtualIds: evalContext,
            resIds: [],
            resModel: this.env.searchModel.resModel,
        };
    }

    get renderingContext() {
        return {
            context: this.helpRecord.context,
            data: this.props.data,
            __comp__: Object.assign(Object.create(this), { this: this }),
            action_help: this.props.actionHelp,
        };
    }
}
