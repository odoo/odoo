import { Component, onWillStart, onWillUpdateProps, proxy, signal, t, useProps } from "@odoo/owl";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { useService } from "@web/core/utils/hooks";
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
            // data of the help, returned by the `data_method` of the model
            this.state = proxy({ data: {} });
            if (this.helpArchInfo.dataMethod) {
                this.orm = useService("orm");
                onWillStart(() => this.loadData());
                onWillUpdateProps(() => this.loadData());
            }
        }
    }

    /**
     * Calls the `data_method` of the help with the current domain and context,
     * if they changed since the last call. The result is cached: the cached data
     * are displayed directly, and updated if the server returns other ones.
     */
    async loadData() {
        const { context, domain, resModel } = this.env.searchModel;
        const key = JSON.stringify([domain, context]);
        if (key !== this.dataKey) {
            this.dataKey = key;
            const orm = this.orm.cache({
                type: "disk",
                update: "always",
                callback: (result, hasChanged) => {
                    if (hasChanged && key === this.dataKey) {
                        this.state.data = result;
                    }
                },
            });
            const data = await orm.call(resModel, this.helpArchInfo.dataMethod, [domain], {
                context,
            });
            // ignore the result if the search changed in the meantime
            if (key === this.dataKey) {
                this.state.data = data;
            }
        }
    }

    get showDefaultHelper() {
        return !this.props.noContentHelp;
    }

    /**
     * Fake "record" given to the ViewButtons of the help, and used to evaluate
     * `invisible` attributes: there is no record, only the action context and
     * the data of the help.
     */
    get helpRecord() {
        const context = this.env.searchModel?.context || {};
        const evalContext = { ...getBasicEvalContext({ context }), data: this.state?.data || {} };
        return {
            context,
            evalContext,
            evalContextWithVirtualIds: evalContext,
            resIds: [],
            resModel: this.env.searchModel?.resModel,
        };
    }

    get renderingContext() {
        return {
            context: this.helpRecord.context,
            data: this.state?.data || {},
            __comp__: Object.assign(Object.create(this), { this: this }),
            action_help: this.props.noContentHelp,
        };
    }
}
