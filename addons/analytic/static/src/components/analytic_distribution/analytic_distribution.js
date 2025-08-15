/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { evaluateExpr } from "@web/core/py_js/py";
import { getNextTabableElement, getPreviousTabableElement } from "@web/core/utils/ui";
import { usePosition } from "@web/core/position_hook";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { shallowEqual } from "@web/core/utils/arrays";
import { roundDecimals } from "@web/core/utils/numbers";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { useRecordObserver } from "@web/model/relational_model/utils";

import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { TagsList } from "@web/core/tags_list/tags_list";
import { useOpenMany2XRecord } from "@web/views/fields/relational_utils";
import { formatPercentage } from "@web/views/fields/formatters";

import { Record } from "@web/model/record";
import { Field } from "@web/views/fields/field";
import {
    Component,
    useState,
    useRef,
    useExternalListener,
    onWillStart,
    onPatched,
} from "@odoo/owl";

export class AnalyticDistribution extends Component {
    static template = "analytic.AnalyticDistribution";
    static components = {
        TagsList,
        Record,
        Field,
    }

    static props = {
        ...standardFieldProps,
        business_domain: { type: String, optional: true },
        account_field: { type: String, optional: true },
        product_field: { type: String, optional: true },
        amount_field: { type: String, optional: true },
        business_domain_compute: { type: String, optional: true },
        force_applicability: { type: String, optional: true },
        allow_save: { type: Boolean, optional: true },
    }

    setup(){
        this.orm = useService("orm");
        this.batchedOrm = useService("batchedOrm");

        this.state = useState({
            showDropdown: false,
            formattedData: [],
        });

        this.widgetRef = useRef("analyticDistribution");
        this.dropdownRef = useRef("analyticDropdown");
        this.mainRef = useRef("mainElement");
        this.addLineButton = useRef("addLineButton");
        usePosition("analyticDropdown", () => this.widgetRef.el);

        this.nextId = 1;
        this.focusSelector = false;

        this.currentValue = this.props.record.data[this.props.name];

        onWillStart(this.willStart);
        useRecordObserver(this.willUpdateRecord.bind(this));
        onPatched(this.patched);

        useExternalListener(window, "click", this.onWindowClick, true);
        useExternalListener(window, "resize", this.onWindowResized);

        this.openTemplate = useOpenMany2XRecord({
            resModel: "account.analytic.distribution.model",
            activeActions: {
                create: true,
                edit: false,
                write: true,
            },
            isToMany: false,
            onRecordSaved: async (record) => {
                if (!this.props.record.model.multiEdit) {
                    this.mainRef.el.focus();
                }
            },
            onClose: () => {
                if (!this.props.record.model.multiEdit) {
                    this.mainRef.el.focus();
                }
            },
            fieldString: _t("Analytic Distribution Model"),
        });
        this.allPlans = [];
        this.lastAccount = this.props.account_field && this.props.record.data[this.props.account_field] || false;
        this.lastProduct = this.props.product_field && this.props.record.data[this.props.product_field] || false;
    }

    // Lifecycle
    async willStart() {
        if (this.editingRecord) {
            // for performance in list views, plans are not retrieved until they are required.
            await this.fetchAllPlans(this.props);
        }
        await this.jsonToData(this.props.record.data[this.props.name]);
    }

    async willUpdateRecord(record) {
        // Unless force_applicability, Plans need to be retrieved again as the product or account might have changed
        // and thus different applicabilities apply
        // or a model applies that contains unavailable plans
        // This should only execute when these fields have changed, therefore we use the `_field` props.
        const valueChanged =
            JSON.stringify(this.currentValue) !==
            JSON.stringify(record.data[this.props.name]);
        const currentAccount = this.props.account_field && record.data[this.props.account_field] || false;
        const currentProduct = this.props.product_field && record.data[this.props.product_field] || false;
        const accountChanged = !shallowEqual(this.lastAccount, currentAccount);
        const productChanged = !shallowEqual(this.lastProduct, currentProduct);
        if (valueChanged || accountChanged || productChanged) {
            if (!this.props.force_applicability) {
                await this.fetchAllPlans({ record });
            }
            this.lastAccount = accountChanged && currentAccount || this.lastAccount;
            this.lastProduct = productChanged && currentProduct || this.lastProduct;
            await this.jsonToData(record.data[this.props.name]);
        }
        this.currentValue = record.data[this.props.name];
    }

    patched() {
        this.focusToSelector();
    }

    /**
     * Computes the totals for each account, grouped by plan (primarily used in tags)
     * @returns {Object}
     */
    accountTotalsByPlan() {
        const accountTotals = {};
        this.state.formattedData.map((line) => {
            line.analyticAccounts.map((column) => {
                if (column.accountId) {
                    let {
                        accId = column.accountId,
                        accName = column.accountDisplayName,
                        total = 0.0,
                        planId = column.accountRootPlanId,
                        planColor = column.accountColor,
                    } = accountTotals[column.accountRootPlanId]?.[column.accountId] || {};

                    total += roundDecimals(line.percentage, this.decimalPrecision.digits[1] + 2);

                    accountTotals[planId] = accountTotals[planId] || {};
                    accountTotals[planId][accId] = { accId, accName, planId, total, planColor};
                }
            })
        });
        return accountTotals;
    }

    /**
     * Computes the totals for each plan (used in the table headers)
     * @returns {Object}
     */
    planTotals() {
        const summary = this.accountTotalsByPlan();
        this.allPlans.map((plan) => {
            const planTotal = (summary[plan.id] && Object.values(summary[plan.id]) || []).reduce((prev, next) => prev + next.total, 0.0);
            const className = plan.applicability === "mandatory" && !this.planIsComplete(planTotal) ? 'text-danger' : plan.applicability === "mandatory" ? 'text-success' : '';
            summary[plan.id] = {
                value: planTotal,
                formattedValue: formatPercentage(planTotal, this.decimalPrecision),
                class: className,
                applicability: plan.applicability,
            }
        });
        return summary;
    }

    planIsComplete(total) {
        return roundDecimals(total, this.decimalPrecision.digits[1] + 2) === 1;
    }

    /**
     * Converts the account Totals to a list of tags
     * PlanA  PlanB  PlanC  Percentage
     * A1                   100
     *        B1            80.123     => ["A1", "80.12% B1", "C1"]
     *               C1     100
     *
     * PlanA  PlanB  PlanC  Percentage
     * A1     B1     C1     50
     * A2     B1     C1     50         => ["50% A1 | 50% A2 | 50% A3", "150% B1", "C1 | 50% C2"]
     * A3     B1     C2     50
     * @returns [List] of tag objects
     */
    planSummaryTags() {
        const accountTotals = this.accountTotalsByPlan();
        return Object.values(accountTotals).map((planSummary) => {
            const accs = Object.values(planSummary);
            return {
                id: accs[0].planId,
                text: accs.reduce((p, n) => p + (p.length ? " | " : "") + (this.planIsComplete(n.total) ? n.accName : `${formatPercentage(n.total)} ${n.accName}`) , ""),
                colorIndex: accs[0].planColor,
                onClick: (ev) => this.tagClicked(ev),
            };
        });
    }

    plansToArray() {
        return this.allPlans.map((plan) => ({
            planId: plan.id,
            planName: plan.name,
            planColor: plan.color,
        }));
    }

    async jsonToData(jsonFieldValue) {
        const analyticAccountIds = jsonFieldValue ? Object.keys(jsonFieldValue).map((key) => key.split(',')).flat().map((id) => parseInt(id)) : [];
        const analyticAccountDict = analyticAccountIds.length ? await this.fetchAnalyticAccounts([["id", "in", analyticAccountIds]]) : [];

        let distribution = [];
        let accountNotFound = false;

        for (const [accountIds, percentage] of Object.entries(jsonFieldValue)) {
            const defaultVals = this.plansToArray(); // empty if the popup was not opened
            const ids = accountIds.split(',');

            for (const id of ids) {
                const account = analyticAccountDict[parseInt(id)];
                if (account) {
                    // since tags are displayed even though plans might not be retrieved (ie defaultVals is empty)
                    // push the accounts anyway, as order doesn't matter
                    // once the popup is opened, plans are fetched and the analyticAccounts list will be ordered
                    Object.assign(defaultVals.find((plan) => plan.planId == account.root_plan_id[0]) || defaultVals.push({}) && defaultVals[defaultVals.length-1],
                    {
                        accountId: parseInt(id),
                        accountDisplayName: account.display_name,
                        accountColor: account.color,
                        accountRootPlanId: account.root_plan_id[0],
                    });
                } else {
                    accountNotFound = true;
                }
            }
            distribution.push({
                analyticAccounts: defaultVals,
                percentage: percentage / 100,
                id: this.nextId++,
            })
        }
        this.state.formattedData = distribution;
        if (accountNotFound) {
            // Analytic accounts in the json were not found, save the json without them
            await this.save();
        }
    }

    recordProps(line) {
        const analyticAccountFields = {
            id: { type: "int" },
            display_name: { type: "char" },
            color: { type: "int" },
            plan_id: { type: "many2one" },
            root_plan_id: { type: "many2one" },
        };
        let recordFields = {};
        const values = {};
        // Analytic Account fields
        line.analyticAccounts.map((account) => {
            const fieldName = `x_plan${account.planId}_id`;
            recordFields[fieldName] = {
                string: account.planName,
                relation: "account.analytic.account",
                type: "many2one",
                related: {
                    fields: analyticAccountFields,
                    activeFields: analyticAccountFields,
                },
                // company domain might be required here
                domain: [["root_plan_id", "=", account.planId]],
            };
            values[fieldName] =  account?.accountId || false;
        });
        // Percentage field
        recordFields['percentage'] = {
            string: _t("Percentage"),
            type: "percentage",
            cellClass: "numeric_column_width",
            ...this.decimalPrecision,
        };
        values['percentage'] = line.percentage;
        // Value field copied from original
        if (this.props.amount_field) {
            const { string, name, type, currency_field } = this.props.record.fields[this.props.amount_field];
            recordFields[name] = { string, name, type, currency_field, cellClass: "numeric_column_width" };
            values[name] = this.props.record.data[name] * values['percentage'];
            // Currency field
            if (currency_field) {
                // TODO: check web_read network request
                const { string, name, type, relation } = this.props.record.fields[currency_field];
                recordFields[currency_field] = { name, string, type, relation, invisible: true };
                values[currency_field] = this.props.record.data[currency_field][0];
            }
        }
        return {
            fields: recordFields,
            values: values,
            activeFields: recordFields,
            onRecordChanged: async (record, changes) => await this.lineChanged(record, changes, line),
        }
    }

    accountCount(line) {
        return line.analyticAccounts.map((acc) => acc.accountId).filter(Boolean).length;
    }

    lineIsValid(line) {
        return this.accountCount(line) && line.percentage;
    }

    // ORM
    fetchPlansArgs({ record }) {
        let args = {};
        if (this.props.business_domain_compute) {
            args['business_domain'] = evaluateExpr(this.props.business_domain_compute, record.evalContext);
        }
        if (this.props.business_domain) {
            args['business_domain'] = this.props.business_domain;
        }
        if (this.props.product_field && record.data[this.props.product_field]) {
            args['product'] = record.data[this.props.product_field][0];
        }
        if (this.props.account_field && record.data[this.props.account_field]) {
            args['account'] = record.data[this.props.account_field][0];
        }
        if (this.props.force_applicability) {
            args['applicability'] = this.props.force_applicability;
        }
        const existing_account_ids = Object.keys(record.data[this.props.name]).map((k) => k.split(",")).flat().map((i) => parseInt(i));
        if (existing_account_ids.length) {
            args['existing_account_ids'] = existing_account_ids;
        }
        if (record.data.company_id) {
            args['company_id'] = record.data.company_id[0];
        }
        return args;
    }

    async fetchAllPlans(props) {
        const argsPlan = this.fetchPlansArgs(props);
        this.allPlans = await this.orm.call("account.analytic.plan", "get_relevant_plans", [], argsPlan);
    }

    async fetchAnalyticAccounts(domain) {
        const args = {
            domain: domain,
            fields: ["id", "display_name", "root_plan_id", "color"],
            context: [],
        }
        // batched call
        const records = await this.batchedOrm.read("account.analytic.account", domain[0][2], args.fields, {});
        return Object.assign({}, ...records.map((r) => {
            const {id, ...rest} = r;
            return {[id]: rest};
        }));
    }

    // Editing Distributions
    async lineChanged(record, changes, line) {
        // record analytic account changes to the state
        for (const account of line.analyticAccounts) {
            const selected = record.data[`x_plan${account.planId}_id`];
            account.accountId = selected[0];
            account.accountDisplayName = selected[1];
            account.accountColor = account.planColor;
            account.accountRootPlanId = account.planId;
        }
        // record percentage or value changes
        if (changes.percentage != line.percentage) {
            roundDecimals(line.percentage = record.data.percentage, this.decimalPrecision.digits[1] + 2);
        } else if (
            this.valueColumnEnabled &&
            changes[this.props.amount_field] != line[this.props.amount_field]
        ) {
            line.percentage = roundDecimals(
                record.data[this.props.amount_field] / this.props.record.data[this.props.amount_field],
                this.decimalPrecision.digits[1] + 2);
        }
    }

    // Getters
    get valueColumnEnabled() {
        return Boolean(this.props.amount_field && this.props.record.data[this.props.amount_field]);
    }

    get decimalPrecision() {
        return { digits: [12, this.props.record.data.analytic_precision || 2] };
    }

    get allowSave() {
        return this.props.allow_save && this.state.formattedData.some((line) => this.lineIsValid(line));
    }

    get editingRecord() {
        return !this.props.readonly;
    }

    get isDropdownOpen() {
        return this.state.showDropdown && !!this.dropdownRef.el;
    }

    // actions
    addLine() {
        let maxMandatory = 0, maxOptional = 0, hasMandatory = false;

        Object.values(this.planTotals()).filter((plan) => plan.value < 1).map((plan) => {
            if (plan.applicability == "mandatory"){
                maxMandatory = Math.max(plan.value, maxMandatory);
                hasMandatory = true;
            } else {
                maxOptional = Math.max(plan.value, maxOptional);
            }
        });
        let noPlanTotal = this.state.formattedData.filter((line) => !this.accountCount(line)).reduce((p, n) => p + n.percentage, 0);
        const remainder = roundDecimals(1 - (hasMandatory ? maxMandatory : (maxOptional || noPlanTotal)), this.decimalPrecision.digits[1] + 2);
        const lineToAdd = {
            id: this.nextId++,
            analyticAccounts: this.plansToArray(),
            percentage: Math.max(remainder, 0) || 1,
        }
        this.state.formattedData.push(lineToAdd);
        this.setFocusSelector(`[name=line_${this.state.formattedData.length - 1}] td:first-of-type`);
    }

    deleteLine(index) {
        this.state.formattedData.splice(index, 1);
        if (!this.state.formattedData.length) {
            this.addLine();
        }
    }

    dataToJson() {
        const result = {};
        this.state.formattedData = this.state.formattedData.filter((line) => this.accountCount(line));
        this.state.formattedData.map((line) => {
            const key = line.analyticAccounts.reduce((p, n) => p.concat(n.accountId ? n.accountId : []), []);
            result[key] = (result[key] || 0) + line.percentage * 100;
        });
        return result;
    }

    async save() {
        await this.props.record.update({ [this.props.name]: this.dataToJson() });
    }

    onSaveNew() {
        this.closeAnalyticEditor();
        const { record, product_field, account_field } = this.props;
        this.openTemplate({ resId: false, context: {
            'default_analytic_distribution': this.dataToJson(),
            'default_partner_id': record.data['partner_id'] ? record.data['partner_id'][0] : undefined,
            'default_product_id': product_field ? record.data[product_field][0] : undefined,
            'default_account_prefix': account_field ? record.data[account_field][1].substr(0, 3) : undefined,
        }});
    }

    forceCloseEditor() {
        // focus to the main Element but the dropdown should not open
        this.preventOpen = true;
        this.closeAnalyticEditor();
        this.mainRef.el.focus();
        this.preventOpen = false;
    }

    closeAnalyticEditor() {
        this.save();
        this.state.showDropdown = false;
    }

    async openAnalyticEditor() {
        if (!this.allPlans.length) {
            await this.fetchAllPlans(this.props);
            await this.jsonToData(this.props.record.data[this.props.name]);
        }
        if (!this.state.formattedData.length) {
            await this.addLine();
        }
        this.setFocusSelector("[name='line_0'] td:first-of-type");
        this.state.showDropdown = true;
    }

    async tagClicked(ev) {
        if (this.editingRecord && !this.isDropdownOpen) {
            // TODO: focus is not working when tag is clicked while on an editable line
            await this.openAnalyticEditor();
        }
        if (this.isDropdownOpen) {
            this.setFocusSelector("[name='line_0'] td:first-of-type");
            this.focusToSelector();
            ev.stopPropagation();
        }
    }

    // Focus
    onMainElementFocus(ev) {
        if (!this.isDropdownOpen && !this.preventOpen) {
            this.openAnalyticEditor();
        }
    }

    focusToSelector() {
        if (this.focusSelector && this.isDropdownOpen) {
            this.focus(this.adjacentElementToFocus("next", this.dropdownRef.el.querySelector(this.focusSelector)));
        }
        this.focusSelector = false;
    }

    setFocusSelector(selector) {
        this.focusSelector = selector;
    }

    adjacentElementToFocus(direction, el = null) {
        if (!this.isDropdownOpen) {
            return null;
        }
        if (!el) {
            el = this.dropdownRef.el;
        }
        return direction == "next" ? getNextTabableElement(el) : getPreviousTabableElement(el);
    }

    focusAdjacent(direction) {
        const elementToFocus = this.adjacentElementToFocus(direction);
        if (elementToFocus){
            this.focus(elementToFocus);
            return true;
        }
        return false;
    }

    focus(el) {
        if (!el) return;
        el.focus();
        if (["INPUT", "TEXTAREA"].includes(el.tagName)) {
            if (el.selectionStart) {
                el.selectionStart = 0;
                el.selectionEnd = el.value.length;
            }
            el.select();
        }
    }

    // Keys and Clicks
    async onWidgetKeydown(ev) {
        if (!this.editingRecord) {
            return;
        }
        const hotkey = getActiveHotkey(ev);
        switch (hotkey) {
            case "enter":
            case "tab": {
                if (this.isDropdownOpen) {
                    const closestCell = ev.target.closest("td, th");
                    const row = closestCell.parentElement;
                    const line = this.state.formattedData[parseInt(row.id)];
                    if (this.adjacentElementToFocus("next") == this.addLineButton.el && line && this.lineIsValid(line)) {
                        this.addLine();
                        break;
                    }
                    this.focusAdjacent("next") || this.forceCloseEditor();
                    break;
                };
                return;
            }
            case "shift+tab": {
                if (this.isDropdownOpen) {
                    this.focusAdjacent("previous") || this.forceCloseEditor();
                    break;
                };
                return;
            }
            case "escape": {
                if (this.isDropdownOpen) {
                    this.forceCloseEditor();
                    break;
                }
            }
            case "arrowdown": {
                if (!this.isDropdownOpen) {
                    this.onMainElementFocus();
                    break;
                }
                return;
            }
            default: {
                return;
            }
        }
        ev.preventDefault();
        ev.stopPropagation();
    }

    onWindowClick(ev) {
        /*
        Dropdown should be closed only if all these conditions are true:
            - dropdown is open
            - click is outside widget element (widgetRef)
            - Either:
                - The click is not inside an active modal with a list/kanban view (search more modal)
                    and not inside a popover (search bar menu)
                OR
                - The widget is inside an active modal
            - click is not targeting document dom element (drag and drop search more modal)
        */

        const selectors = [
            ".o_popover",
            ".modal:not(.o_inactive_modal):not(:has(.o_act_window))",
        ];
        if (this.isDropdownOpen
            && !this.widgetRef.el.contains(ev.target)
            && (!ev.target.closest(selectors.join(","))
                || document.querySelector(".modal:not(.o_inactive_modal)").contains(this.widgetRef.el))
            && !ev.target.isSameNode(document.documentElement)
           ) {
            this.forceCloseEditor();
        }
    }

    onWindowResized() {
        // popup ui is ugly when window is resized, so close it
        if (this.isDropdownOpen && !isMobileOS()) {
            this.forceCloseEditor();
        }
    }
}

export const analyticDistribution = {
    component: AnalyticDistribution,
    supportedTypes: ["char", "text"],
    fieldDependencies: [{ name:"analytic_precision", type: "integer" }],
    supportedOptions: [
        {
            label: _t("Disable save"),
            name: "disable_save",
            type: "boolean",
        },
        {
            label: _t("Force applicability"),
            name: "force_applicability",
            type: "boolean",
        },
        {
            label: _t("Business domain"),
            name: "business_domain",
            type: "string",
        },
        {
            label: _t("Product field"),
            name: "product_field",
            type: "field",
            availableTypes: ["many2one"],
        },
        {
            label: _t("Amount field"),
            name: "amount_field",
            type: "field",
            availableTypes: ["monetary"],
        },
        {
            label: _t("Account field"),
            name: "account_field",
            type: "field",
            availableTypes: ["many2one"],
        }
    ],
    extractProps: ({ attrs, options }) => ({
        business_domain: options.business_domain,
        account_field: options.account_field,
        product_field: options.product_field,
        amount_field: options.amount_field,
        business_domain_compute: attrs.business_domain_compute,
        force_applicability: options.force_applicability,
        allow_save: !options.disable_save,
    }),
};

registry.category("fields").add("analytic_distribution", analyticDistribution);
