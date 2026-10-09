import { Component, signal, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { getBasicEvalContext } from "@web/model/relational_model/utils";
import { HelpCompiler } from "@web/views/help/help_compiler";
import { HelpWidget } from "@web/views/help/help_widget";
import { ViewButton } from "@web/views/view_button/view_button";
import { useViewButtons } from "@web/views/view_button/view_button_hook";
import { useViewCompiler } from "@web/views/view_compiler";

export class ActionHelper extends Component {
    static template = "web.ActionHelper";
    static components = { HelpWidget, ViewButton };
    props = useProps({
        noContentHelp: t.string().optional(),
    });

    rootRef = signal.ref();

    setup() {
        // help view (see `help_id` view attribute), inlined in the view arch
        this.helpArchInfo = this.env.config?.noContentHelpArchInfo;
        if (this.helpArchInfo) {
            const templates = useViewCompiler(
                HelpCompiler,
                { help: this.helpArchInfo.xmlDoc },
                { recordExpr: "__comp__.helpRecord" }
            );
            this.helpTemplate = templates.help;
            this.evaluateBooleanExpr = evaluateBooleanExpr;
            // buttons of the help are executed on an empty recordset, and the
            // view is reloaded afterwards
            useViewButtons(this.rootRef, { reload: () => this.env.searchModel?.search() });
        }
    }

    get showDefaultHelper() {
        return !this.props.noContentHelp;
    }

    /**
     * Fake "record" given to the ViewButtons of the help, and used to evaluate
     * `invisible` attributes: there is no record, only the action context.
     */
    get helpRecord() {
        const context = this.env.searchModel?.context || {};
        const evalContext = getBasicEvalContext({ context });
        return {
            context,
            evalContext,
            evalContextWithVirtualIds: evalContext,
            resIds: [],
            resModel: this.env.searchModel?.resModel,
        };
    }

    /**
     * Help of the action, or a default text if the action has no help.
     */
    get actionHelp() {
        return this.props.noContentHelp || _t("No data to display");
    }

    get renderingContext() {
        return {
            context: this.helpRecord.context,
            __comp__: Object.assign(Object.create(this), { this: this }),
            action_help: this.actionHelp,
        };
    }
}
