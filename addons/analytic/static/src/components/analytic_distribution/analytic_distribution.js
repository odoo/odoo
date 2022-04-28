/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { evaluateExpr } from "@web/core/py_js/py";
import { getNextTabableElement, getPreviousTabableElement } from "@web/core/utils/ui";
import { usePosition } from "@web/core/position_hook";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { AnalyticAutoComplete } from "../autocomplete/autocomplete";

import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { TagsList } from "@web/views/fields/many2many_tags/tags_list";
import { useOpenMany2XRecord } from "@web/views/fields/relational_utils";
import { parseFloat as oParseFloat } from "@web/views/fields/parsers";
import { formatPercentage } from "@web/views/fields/formatters";

const { Component, useState, useRef, useExternalListener, onWillUpdateProps, onWillStart, onPatched } = owl;


export class AnalyticDistribution extends Component {
    setup(){
        this.orm = useService("orm");

        this.state = useState({
            showDropdown: false,
            list: {},
        });

        this.widgetRef = useRef("analyticDistribution");
        this.dropdownRef = useRef("analyticDropdown");
        this.mainRef = useRef("mainElement");
        usePosition(() => this.widgetRef.el, {
            popper: "analyticDropdown",
        });

        this.nextId = 1;
        this.focusSelector = false;
        this.activeGroup = false;

        onWillStart(this.willStart);
        onWillUpdateProps(this.willUpdate);
        onPatched(this.patched);

        useExternalListener(window, "click", this.onWindowClick, true);

        this.openTemplate = useOpenMany2XRecord({
            resModel: "account.analytic.distribution.model",
            activeActions: {
                canCreate: true,
                canCreateEdit: false,
                canWrite: true,
            },
            isToMany: false,
            onRecordSaved: async (record) => {
                this.mainRef.el.focus();
            },
            onClose: () => {
                this.mainRef.el.focus();
            },
            fieldString: this.env._t("Analytic Distribution Template"),
        });
    }

    // Lifecycle
    async willStart() {
        await this.fetchAllPlans(this.props);
        await this.formatData(this.props);
    }

    async willUpdate(nextProps) {
        // Unless force_applicability, Plans need to be retrieved again as the product or account might have changed
        // and thus different applicabilities apply
        // or a model applies that contains unavailable plans
        // This should only execute when these fields have changed, therefore we use the `_field` props.
        // (consider including the plans in the computed json, python side)
        const valueChanged = JSON.stringify(this.props.value) !== JSON.stringify(nextProps.value);
        if (this.applicabilityParamsChanged(nextProps) || valueChanged) {
            await this.fetchAllPlans(nextProps);
            await this.formatData(nextProps);
        }
    }

    applicabilityParamsChanged(nextProps) {
        if (this.props.force_applicability) {
            return false;
        }
        if (this.props.account_field && this.props.record.data[this.props.account_field] !== nextProps.record.data[this.props.account_field] ||
            this.props.product_field && this.props.record.data[this.props.product_field] !== nextProps.record.data[this.props.product_field]) {
            return true;
        }
        return false;
    }

    async formatData(nextProps) { 
        const data = nextProps.value;
        const analytic_account_ids = Object.keys(data);
        const records = analytic_account_ids.length ? await this.fetchAnalyticAccounts([["id", "in", analytic_account_ids]]) : [];
        if (records.length < data.length) {
            console.log('removing tags... value should be updated');
        }

        let res = Object.assign({}, ...this.allPlans.map((plan) => ({[plan.id]: {...plan, distribution: []}})));
        records.map((record) => {
            res[record.root_plan_id[0]].distribution.push({
                analytic_account_id: record.id,
                percentage: data[record.id],
                id: this.nextId++,
                group_id: record.root_plan_id[0],
                analytic_account_name: record.name,
                color: record.color,
            });
        });

        this.state.list = res;
    }

    patched() {
        this.focusToSelector();
    }

    // ORM
    fetchPlansArgs(nextProps) {
        let args = {};
        if (this.props.business_domain_compute) {
            args['business_domain'] = evaluateExpr(this.props.business_domain_compute, this.props.record.evalContext);
        }
        if (this.props.business_domain) {
            args['business_domain'] = this.props.business_domain;
        }
        if (this.props.product_field && this.props.record.data[this.props.product_field]) {
            args['product'] = this.props.record.data[this.props.product_field][0];
        }
        if (this.props.account_field && this.props.record.data[this.props.account_field]) {
            args['account'] = this.props.record.data[this.props.account_field][0];
        }
        if (this.props.force_applicability) {
            args['applicability'] = this.props.force_applicability;
        }
        const existing_account_ids = Object.keys(nextProps.value).map((i) => parseInt(i));
        if (existing_account_ids.length) {
            args['existing_account_ids'] = existing_account_ids;
        }
        return args;
    }

    async fetchAllPlans(nextProps) {
        // TODO: Optimize to execute once for all records when `force_applicability` is set
        const argsPlan =  this.fetchPlansArgs(nextProps);
        this.allPlans = await this.orm.call("account.analytic.plan", "get_relevant_plans", [], argsPlan);
    }

    async fetchAnalyticAccounts(domain, limit=null) {
        const args = {
            domain: domain,
            fields: ["id", "name", "root_plan_id", "color"],
            context: [],
        }
        if (limit) {
            args['limit'] = limit;
        }
        return await this.orm.call("account.analytic.account", "search_read", [], args);
    }

    // Autocomplete
    get sourcesAnalyticAccount() {
        return [this.optionsSourceAnalytic];
    }

    get optionsSourceAnalytic() {
        return {
            placeholder: this.env._t("Loading..."),
            options: this.loadOptionsSourceAnalytic.bind(this),
        };
    }

    async loadOptionsSourceAnalytic(request) {
        let domain = [['id', 'not in', this.existingAnalyticAccountIDs]];

        if (this.activeGroup) {
            domain.push(['root_plan_id', '=', this.activeGroup]);
        }

        const records = await this.fetchAnalyticAccounts([...domain, ["name", "ilike", request]], 7);

        let options = records.map((result) => ({
            value: result.id,
            label: result.name,
            group_id: result.root_plan_id[0],
            color: result.color,
        }));

        if (!options.length) {
            options.push({
                label: this.env._t("No Analytic Accounts for this plan"),
                classList: "o_m2o_no_result",
                unselectable: true,
            });
        }

        return options;
    }

    groupAutocompleteFocus(group_id) {
        this.activeGroup = group_id;
    }

    autoCompleteInput(dist_tag, {inputValue}) {
        if (inputValue === "") {
            dist_tag.analytic_account_id = "";
        }
    }

    // Editing Distributions
    async onSelect(option, params, tag) {
        const selected_option = Object.getPrototypeOf(option);
        tag.analytic_account_id = parseInt(selected_option.value);
        tag.analytic_account_name = selected_option.label;
        tag.color = selected_option.color;
        this.setFocusSelector(`.tag_${tag.id} .o_analytic_percentage`);
    }

    async percentageChanged(dist_tag, ev) {
        dist_tag.percentage = this.parse(ev.target.value);

        if (this.remainderByGroup(dist_tag.group_id)) {
            this.setFocusSelector(`#plan_${dist_tag.group_id} .incomplete .o_analytic_account_name`);
        }
        this.autoFill();
    }

    deleteTag(id) {
        for (const group_id in this.list) {
            this.list[group_id].distribution = this.list[group_id].distribution.filter((dist_tag) => dist_tag.id != id);
            if (this.list[group_id].applicability === 'mandatory' && this.remainderByGroup(group_id)) this.addLineToGroup(group_id);
        }
        if (!this.isDropdownOpen){
            this.save();
        }
    }

    addLineToGroup(id) {
        const tag_cnt_diff = this.list[id].distribution.length - this.listReadyByGroup(id).length;
        if (!tag_cnt_diff) {
            this.list[id].distribution.push(this.newTag(id));
        } else {
            //all tags are not ready - update the value of tag without analytic account or add
            const tagToUpdate = this.list[id].distribution.filter((t) => !this.tagIsReady(t) && !t.analytic_account_id)[0];
            if (!!tagToUpdate) {
                tagToUpdate.percentage = this.remainderByGroup(id);
            } else {
                this.list[id].distribution.push(this.newTag(id));
            }
        }
    }

    // Getters
    get tags() {
        return this.listReady.map((dist_tag) => ({
            id: dist_tag.id,
            text: `${dist_tag.analytic_account_name}${dist_tag.percentage > 99.99 && dist_tag.percentage < 100.01 ? "" : " " + this.formatPercentage(dist_tag.percentage)}`,
            colorIndex: dist_tag.color,
            group_id: dist_tag.group_id,
            onClick: (ev) => this.tagClicked(ev, dist_tag.id),
            onDelete: this.editingRecord ? () => this.deleteTag(dist_tag.id) : undefined
        }));
    }

    get listForJson() {
        let res = {};
        this.listReady.map(({analytic_account_id, percentage}) => {
            res[parseInt(analytic_account_id)] = percentage;
        });
        return res;
    }

    get firstIncompletePlanId() {
        for (const group_id in this.list) {
            const group_status = this.groupStatus(group_id);
            if (["orange", "red"].includes(group_status)) return group_id;
        }
        return 0;
    }

    get existingAnalyticAccountIDs() {
        return this.listFlat.filter((i) => !!i.analytic_account_id).map((i) => i.analytic_account_id);
    }

    get listReady() {
        return this.listFlat.filter((dist_tag) => this.tagIsReady(dist_tag));
    }

    get listFlat() {
        return Object.values(this.list).flatMap((g) => g.distribution);
    }

    get list() {
        return this.state.list;
    }

    get sortedList() {
        return Object.values(this.list).sort((a, b) => {
            const aApp = a.applicability,
                  bApp = b.applicability;
            return aApp > bApp ? 1 : aApp < bApp ? -1 : 0;
        });
    }

    get allowSave() {
        for (const group_id in this.list) {
            if (['orange', 'red'].includes(this.groupStatus(group_id))) return false;
        }
        return this.props.allow_save;
    }

    get editingRecord() {
        return !this.props.readonly;
    }

    get isDropdownOpen() {
        return this.state.showDropdown && !!this.dropdownRef.el;
    }

    applicabilityStatus(group_id) {
        const group = this.list[group_id];
        const status = this.groupStatus(group_id);
        let description;
        switch(status){
            case "gray":
                description = this.env._t("Editing (OK)");
                break;
            case "orange": {
                description = this.env._t("Editing (Incomplete)");
                break;
            }
            case "red": {
                description = this.env._t("Invalid");
                break;
            }
            case "green": {
                description = this.env._t("OK");
                break;
            }
        }
        return `${group.applicability.charAt(0).toUpperCase()}${group.applicability.slice(1)} - ${description}`;
    }

    groupStatus(id) {
        const group = this.list[id];
        const ready_tags = this.listReadyByGroup(id);
        if (group.distribution.length > ready_tags.length) {
            return group.applicability === 'mandatory' ? 'orange' : 'gray';
        }
        const sum = this.sumByGroup(id);
        if (group.applicability === 'mandatory' && (sum < 99.99 || sum >= 100.01)){
            return 'red';
        }
        return 'green';
    }

    listReadyByGroup(id) {
        return this.list[id].distribution.filter((tag) => this.tagIsReady(tag));
    }

    tagIsReady({analytic_account_id, percentage}) {
        return !!analytic_account_id && !!percentage;
    }

    sumByGroup(id) {
        return this.listReadyByGroup(id).reduce((prev, next) => prev + (parseFloat(next.percentage) || 0), 0);
    }

    remainderByGroup(id) {
        return 100 - Math.min(this.sumByGroup(id), 100);
    }

    // actions
    newTag(group_id) {
        return {
            id: this.nextId++,
            group_id: group_id,
            analytic_account_id: null,
            analytic_account_name: "",
            percentage: this.remainderByGroup(group_id),
            color: this.list[group_id].color,
        }
    }

    autoFill() {
        for (const group of this.allPlans.filter((p) => p.all_account_count > 0)){
            if (this.remainderByGroup(group.id)) {
                this.addLineToGroup(group.id);
            }
        }
    }

    cleanUp() {
        for (const group_id in this.list){
            this.list[group_id].distribution = this.listReadyByGroup(group_id);
        }
    }

    validate() {
        for (const group_id in this.list) {
            if (this.groupStatus(group_id) === 'red') {
                this.invalidate();
                return false;
            }
        }
        return true;
    }

    invalidate() {
        this.props.record.setInvalidField(this.props.name);
    }

    async save() {
        const currentDistribution = this.listForJson;
        const dataToSave = currentDistribution;
        await this.props.update(dataToSave);
        this.validate();
    }

    onSaveNew() {
        this.openTemplate({ resId: false, context: {
            'default_analytic_distribution': this.listForJson,
        }});
        this.closeAnalyticEditor();
    }

    forceCloseEditor() {
        // focus to the main Element but the dropdown should not open
        this.preventOpen = true;
        this.closeAnalyticEditor();
        this.mainRef.el.focus();
        this.preventOpen = false;
    }

    closeAnalyticEditor() {
        this.cleanUp();
        this.save();
        this.state.showDropdown = false;
    }

    openAnalyticEditor() {
        this.autoFill();
        const incompletePlan = this.firstIncompletePlanId;
        this.setFocusSelector(incompletePlan ? `#plan_${incompletePlan} .incomplete`: ".analytic_json_popup");
        this.state.showDropdown = true;
    }

    tagClicked(ev, id) {
        if (this.editingRecord && !this.isDropdownOpen) {
            this.openAnalyticEditor();
        }
        if (this.isDropdownOpen) {
            this.setFocusSelector(`.tag_${id} .o_analytic_percentage`);
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
        if (!!this.focusSelector && this.isDropdownOpen) {
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
    onWidgetKeydown(ev) {
        if (!this.editingRecord) {
            return;
        }
        const hotkey = getActiveHotkey(ev);
        switch (hotkey) {
            case "enter":
            case "tab": {
                if (this.isDropdownOpen) {
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
        if (this.isDropdownOpen && this.dropdownRef.el && !this.dropdownRef.el.contains(ev.target) && !this.widgetRef.el.contains(ev.target)) {
            this.closeAnalyticEditor();
        }
    }

    // formatters and parsers
    parse(value) {
        try {
            return typeof value === 'string' || value instanceof String ? oParseFloat(value.replace('%', '')) : value;
        } catch (_error) {
            return 0;
        }
    }

    formatPercentage(value) {
        return formatPercentage(value / 100, { digits: [false, 2] });
    }
}
AnalyticDistribution.template = "analytic_distribution";
AnalyticDistribution.supportedTypes = ["char", "text"];
AnalyticDistribution.components = {
    AnalyticAutoComplete,
    TagsList,
}
AnalyticDistribution.props = {
    ...standardFieldProps,
    business_domain: { type: String, optional: true },
    account_field: { type: String, optional: true },
    product_field: { type: String, optional: true },
    business_domain_compute: { type: String, optional: true },
    force_applicability: { type: String, optional: true },
    allow_save: { type: Boolean },
}
AnalyticDistribution.extractProps = ({ field, attrs }) => {
    return {
        business_domain: attrs.options.business_domain,
        account_field: attrs.options.account_field,
        product_field: attrs.options.product_field,
        business_domain_compute: attrs.business_domain_compute,
        force_applicability: attrs.options.force_applicability,
        allow_save: !Boolean(attrs.options.disable_save),
    };
};

export class AnalyticDistributionForm extends AnalyticDistribution {}
AnalyticDistributionForm.template = "analytic_distribution_form";

registry.category("fields").add("analytic_distribution", AnalyticDistribution);
registry.category("fields").add("form.analytic_distribution", AnalyticDistributionForm);
