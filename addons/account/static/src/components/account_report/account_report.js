/** @odoo-module native */
import { AccountReportButtonsBar } from "@account/components/account_report/buttons_bar/buttons_bar";
import { AccountReportCogMenu } from "@account/components/account_report/cog_menu/cog_menu";
import { AccountReportController } from "@account/components/account_report/controller";
import { AccountReportEllipsis } from "@account/components/account_report/ellipsis/ellipsis";
import { AccountReportFilters } from "@account/components/account_report/filters/filters";
import { AccountReportHeader } from "@account/components/account_report/header/header";
import { AccountReportLine } from "@account/components/account_report/line/line";
import { AccountReportLineCell } from "@account/components/account_report/line_cell/line_cell";
import { AccountReportLineName } from "@account/components/account_report/line_name/line_name";
import { AccountReportSearchBar } from "@account/components/account_report/search_bar/search_bar";
import {
    Component,
    onWillDestroy,
    onWillStart,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { useSetupAction } from "@web/core/action_hook";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { standardActionServiceProps } from "@web/webclient/actions";

const log = makeLogger("account.report.ui");

export class AccountReport extends Component {
    static template = "account.AccountReport";
    static props = { ...standardActionServiceProps };
    static components = {
        ControlPanel,
        AccountReportButtonsBar,
        AccountReportCogMenu,
        AccountReportSearchBar,
    };

    static customizableComponents = [
        AccountReportEllipsis,
        AccountReportFilters,
        AccountReportHeader,
        AccountReportLine,
        AccountReportLineCell,
        AccountReportLineName,
    ];
    static defaultComponentsMap = [];

    setup() {
        useLifecycleLog(log);
        this.rootRef = useRef("root");
        useSetupAction({
            rootRef: this.rootRef,
            getLocalState: () => ({
                keep_journal_groups_options: true, // used when using the breadcrumb
            }),
        });
        if (this.props?.state?.keep_journal_groups_options !== undefined) {
            this.props.action.keep_journal_groups_options = true;
        }

        // ControlPanel reads viewSwitcherEntries from the env config; a client action doesn't provide it.
        this.env.config.viewSwitcherEntries = [];

        this.orm = useService("orm");
        this.actionService = useService("action");
        this.ui = useService("ui");
        this.controller = useState(new AccountReportController(this.props.action));
        this.initialQuery = this.props.action.context.default_filter_accounts || "";

        for (const customizableComponent of AccountReport.customizableComponents) {
            AccountReport.defaultComponentsMap[customizableComponent.name] =
                customizableComponent;
        }

        onWillStart(async () => {
            await this.controller.load(this.env);
        });

        onWillDestroy(() => {
            // Since the controller is preloading the sections using a setTimeout, it's never stopped unless we explicitly tell it.
            this.controller.destroyed = true;
        });

        useSubEnv({
            controller: this.controller,
            component: this.getComponent.bind(this),
            template: this.getTemplate.bind(this),
        });
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Custom overrides
    // -----------------------------------------------------------------------------------------------------------------
    static registerCustomComponent(customComponent) {
        registry
            .category("account_reports_custom_components")
            .add(customComponent.name, customComponent);
    }

    get cssCustomClass() {
        return this.controller.options.custom_display_config.css_custom_class || "";
    }

    getComponent(name) {
        const customComponents =
            this.controller.options.custom_display_config.components;

        if (customComponents && customComponents[name]) {
            return registry
                .category("account_reports_custom_components")
                .get(customComponents[name]);
        }

        return AccountReport.defaultComponentsMap[name];
    }

    getTemplate(name) {
        const customTemplates = this.controller.options.custom_display_config.templates;

        if (customTemplates && customTemplates[name]) {
            return customTemplates[name];
        }

        return `account.${name}Customizable`;
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Table
    // -----------------------------------------------------------------------------------------------------------------
    get tableClasses() {
        let classes = "";

        if (this.controller.options.columns.length > 1) {
            classes += " striped";
        }

        if (this.controller.options["horizontal_split"]) {
            classes += " w-50 mx-2";
        }

        return classes;
    }
}

registry.category("actions").add("account_report", AccountReport);
