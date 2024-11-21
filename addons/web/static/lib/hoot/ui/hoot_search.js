/** @odoo-module */

import { Component, useRef, useState, xml } from "@odoo/owl";
import { getActiveElement } from "@web/../lib/hoot-dom/helpers/dom";
import { isRegExpFilter, parseRegExp } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { Suite } from "../core/suite";
import { Tag } from "../core/tag";
import { Test } from "../core/test";
import { EXCLUDE_PREFIX, refresh } from "../core/url";
import {
    INCLUDE_LEVEL,
    STORAGE,
    debounce,
    lookup,
    normalize,
    storageGet,
    storageSet,
    stringify,
    title,
    useWindowListener,
} from "../hoot_utils";
import { HootTagButton } from "./hoot_tag_button";

/**
 * @typedef {{
 * }} HootSearchProps
 *
 * @typedef {"suites" | "tags" | "tests"} SearchCategory
 *
 * @typedef {import("../core/tag").Tag} Tag
 *
 * @typedef {import("../core/test").Test} Test
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Boolean,
    Object: { entries: $entries, values: $values },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 *
 * @param {Record<string, number>} values
 */
const formatIncludes = (values) =>
    $entries(values)
        .filter(([id, value]) => Math.abs(value) === INCLUDE_LEVEL.url)
        .map(([id, value]) => (value >= 0 ? id : `${EXCLUDE_PREFIX}${id}`));

/**
 * @param {string} query
 */
const getPattern = (query) => {
    query = query.match(R_QUERY_CONTENT)[1];
    return parseRegExp(normalize(query), { safe: true });
};

/**
 * /!\ Requires "job" and "category" to be in scope
 *
 * @param {string} tagName
 */
const templateIncludeWidget = (tagName) => /* xml */ `
    <t t-set="includeStatus" t-value="runnerState.includeSpecs[category][job.id] or 0" />
    <t t-set="readonly" t-value="isReadonly(includeStatus)" />

    <${tagName}
        class="flex items-center gap-1 cursor-pointer select-none"
        t-on-click.stop="() => this.toggleInclude(category, job.id)"
    >
        <div
            class="hoot-include-widget h-5 p-px flex items-center relative border rounded-full"
            t-att-class="{
                'border-muted': readonly,
                'border-primary': !readonly,
                'opacity-50': readonly,
            }"
            t-att-title="readonly and 'Cannot change because it depends on a tag modifier in the code'"
            t-on-pointerup="focusSearchInput"
            t-on-change="(ev) => this.onIncludeChange(category, job.id, ev.target.value)"
        >
            <input
                type="radio"
                class="w-4 h-4 cursor-pointer appearance-none"
                t-att-title="!readonly and 'Exclude'"
                t-att-disabled="readonly"
                t-att-name="job.id" value="exclude"
                t-att-checked="includeStatus lt 0"
            />
            <input
                type="radio"
                class="w-4 h-4 cursor-pointer appearance-none"
                t-att-disabled="readonly"
                t-att-name="job.id" value="null"
                t-att-checked="!includeStatus"
            />
            <input
                type="radio"
                class="w-4 h-4 cursor-pointer appearance-none"
                t-att-title="!readonly and 'Include'"
                t-att-disabled="readonly"
                t-att-name="job.id" value="include"
                t-att-checked="includeStatus gt 0"
            />
        </div>
        <t t-if="isTag(job)">
            <HootTagButton tag="job" inert="true" />
        </t>
        <t t-else="">
            <span
                class="flex items-center font-bold whitespace-nowrap overflow-hidden"
                t-att-title="job.fullName"
            >
                <t t-foreach="getShortPath(job.path)" t-as="suite" t-key="suite.id">
                    <span class="text-muted px-1" t-esc="suite.name" />
                    <span class="font-normal">/</span>
                </t>
                <t t-set="isSet" t-value="job.id in runnerState.includeSpecs[category]" />
                <span
                    class="truncate px-1"
                    t-att-class="{
                        'font-extrabold': isSet,
                        'text-pass': includeStatus gt 0,
                        'text-fail': includeStatus lt 0,
                        'text-muted': !isSet and hasIncludeValue,
                        'text-primary': !isSet and !hasIncludeValue,
                        'italic': hasIncludeValue ? includeStatus lte 0 : includeStatus lt 0,
                    }"
                    t-esc="job.name"
                />
            </span>
        </t>
    </${tagName}>
`;

const EMPTY_SUITE = new Suite(null, "…", []);
const SECRET_SEQUENCE = [38, 38, 40, 40, 37, 39, 37, 39, 66, 65];
const R_QUERY_CONTENT = new RegExp(`^\\s*${EXCLUDE_PREFIX}?\\s*(.*)\\s*$`);
const RESULT_LIMIT = 5;

// Template parts, because 16 levels of indent is a bit much

const TEMPLATE_FILTERS_AND_CATEGORIES = /* xml */ `
    <div class="flex mb-2">
        <t t-if="state.query.trim()">
            <button
                class="flex items-center gap-1"
                type="submit"
                title="Run this filter"
                t-on-pointerdown="() => this.updateParams(true)"
            >
                <h4 class="text-primary m-0">
                    Filter using
                    <t t-if="useRegExp">
                        regular expression
                    </t>
                    <t t-else="">
                        text
                    </t>
                </h4>
                <t t-esc="wrappedQuery" />
            </button>
        </t>
        <t t-else="">
            <em class="text-muted ms-1">
                Start typing to show filters...
            </em>
        </t>
    </div>
    <t t-foreach="categories" t-as="category" t-key="category">
        <t t-set="jobs" t-value="state.categories[category][0]" />
        <t t-set="checkedCount" t-value="state.categories[category][1]" />
        <t t-if="jobs?.length">
            <div class="flex flex-col mb-2 max-h-48 overflow-hidden">
                <h4 class="text-primary font-bold flex items-center mb-2">
                    <span class="w-full">
                        <t t-esc="title(category)" />
                        (<t t-esc="checkedCount" />)
                    </span>
                </h4>
                <ul class="flex flex-col overflow-y-auto gap-1">
                    <t t-set="remainingCount" t-value="state.categories[category][2]" />
                    <t t-foreach="jobs" t-as="job" t-key="job.id">
                        ${templateIncludeWidget("li")}
                    </t>
                    <t t-if="remainingCount > 0">
                        <div class="italic">
                            <t t-esc="remainingCount" /> more items ...
                        </div>
                    </t>
                </ul>
            </div>
        </t>
    </t>
`;

const TEMPLATE_SEARCH_DASHBOARD = /* xml */ `
    <div class="flex flex-col gap-4 sm:grid sm:grid-cols-3 sm:gap-0">
        <div class="flex flex-col sm:px-4">
            <h4 class="text-primary font-bold flex items-center mb-2">
                <span class="w-full">
                    Recent searches
                </span>
            </h4>
            <ul class="flex flex-col overflow-y-auto gap-1">
                <t t-foreach="getLatestSearches()" t-as="text" t-key="text_index">
                    <li>
                        <button
                            class="w-full px-2 hover:bg-gray-300 dark:hover:bg-gray-700"
                            type="button"
                            t-on-click.stop="() => this.setQuery(text)"
                            t-esc="text"
                        />
                    </li>
                </t>
            </ul>
        </div>
        <div class="flex flex-col sm:px-4 border-muted sm:border-x">
            <h4 class="text-primary font-bold flex items-center mb-2">
                <span class="w-full">
                    Available suites
                </span>
            </h4>
            <ul class="flex flex-col overflow-y-auto gap-1">
                <t t-foreach="getTop(env.runner.rootSuites)" t-as="job" t-key="job.id">
                    <t t-set="category" t-value="'suites'" />
                    ${templateIncludeWidget("li")}
                </t>
            </ul>
        </div>
        <div class="flex flex-col sm:px-4">
            <h4 class="text-primary font-bold flex items-center mb-2">
                <span class="w-full">
                    Available tags
                </span>
            </h4>
            <ul class="flex flex-col overflow-y-auto gap-1">
                <t t-foreach="getTop(env.runner.tags.values())" t-as="job" t-key="job.id">
                    <t t-set="category" t-value="'tags'" />
                    ${templateIncludeWidget("li")}
                </t>
            </ul>
        </div>
    </div>
`;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/** @extends {Component<HootSearchProps, import("../hoot").Environment>} */
export class HootSearch extends Component {
    static components = { HootTagButton };

    static props = {};

    static template = xml`
        <t t-set="hasIncludeValue" t-value="getHasIncludeValue()" />
        <t t-set="isRunning" t-value="runnerState.status === 'running'" />
        <search class="HootSearch flex-1" t-ref="root" t-on-keydown="onKeyDown">
            <form class="relative" t-on-submit.prevent="refresh">
                <div class="hoot-search-bar flex border rounded items-center bg-base px-1 gap-1 w-full transition-colors">
                    <t t-foreach="getCategoryCounts()" t-as="count" t-key="count.category">
                        <button
                            type="button"
                            class="flex border border-primary rounded"
                            t-att-title="count.tip"
                        >
                            <span class="bg-btn px-1 transition-colors" t-esc="count.category" />
                            <span class="mx-1 flex gap-1">
                                <t t-if="count.include">
                                    <span class="text-pass" t-esc="count.include" />
                                </t>
                                <t t-if="count.exclude">
                                    <span class="text-fail" t-esc="count.exclude" />
                                </t>
                            </span>
                        </button>
                    </t>
                    <input
                        type="search"
                        class="w-full rounded p-1 outline-none"
                        autofocus="autofocus"
                        placeholder="Filter suites, tests or tags"
                        t-ref="search-input"
                        t-att-disabled="isRunning"
                        t-att-value="state.query"
                        t-on-change="onSearchInputChange"
                        t-on-input="onSearchInputInput"
                        t-on-keydown="onSearchInputKeyDown"
                    />
                    <label
                        class="hoot-search-icon cursor-pointer p-1"
                        title="Use regular expression (Alt + R)"
                        tabindex="0"
                        t-on-keydown="onRegExpKeyDown"
                    >
                        <input
                            type="checkbox"
                            class="hidden"
                            t-att-checked="useRegExp"
                            t-att-disabled="isRunning"
                            t-on-change="toggleRegExp"
                        />
                        <i class="fa fa-asterisk text-muted transition-colors" />
                    </label>
                    <label
                        class="hoot-search-icon p-1"
                        title="Debug mode (Alt + D)"
                        t-on-keydown="onDebugKeyDown"
                    >
                        <input
                            type="checkbox"
                            class="hidden"
                            t-att-checked="config.debugTest"
                            t-att-disabled="isRunning"
                            t-on-change="toggleDebug"
                        />
                        <i class="fa fa-bug text-muted transition-colors" />
                    </label>
                </div>
                <t t-if="state.showDropdown">
                    <div class="hoot-dropdown-lg flex flex-col animate-slide-down bg-base text-base absolute mt-1 p-3 shadow rounded shadow z-2">
                        <t t-if="state.empty">
                            ${TEMPLATE_SEARCH_DASHBOARD}
                        </t>
                        <t t-else="">
                            ${TEMPLATE_FILTERS_AND_CATEGORIES}
                        </t>
                    </div>
                </t>
            </form>
        </search>
    `;

    categories = ["suites", "tests", "tags"];
    useTextFilter = false;
    refresh = refresh;
    title = title;

    get useRegExp() {
        return isRegExpFilter(this.state.query.trim());
    }

    get wrappedQuery() {
        const query = this.state.query.trim();
        return this.useRegExp ? query : stringify(query);
    }

    updateSuggestions = debounce(() => {
        this.state.categories = this.findSuggestions();
        this.state.showDropdown = true;
    }, 16);

    setup() {
        const { runner } = this.env;

        runner.beforeAll(() => {
            this.state.categories = this.findSuggestions();
            this.state.empty &&= !this.hasFilters();
        });
        runner.afterAll(() => this.focusSearchInput());

        this.rootRef = useRef("root");
        this.searchInputRef = useRef("search-input");

        this.config = useState(runner.config);
        const query = this.config.filter || "";
        this.state = useState({
            categories: {
                /** @type {Suite[]} */
                suites: [],
                /** @type {Tag[]} */
                tags: [],
                /** @type {Test[]} */
                tests: [],
            },
            disabled: false,
            empty: !query.trim(),
            query,
            showDropdown: false,
        });
        this.runnerState = useState(runner.state);

        useWindowListener(
            "click",
            (ev) => {
                if (this.runnerState.status !== "running") {
                    this.state.showDropdown = ev.composedPath().includes(this.rootRef.el);
                }
            },
            { capture: true }
        );
    }

    /**
     * @param {string} query
     * @param {Map<string, Suite | Tag | Test>} items
     * @param {SearchCategory} category
     */
    filterItems(query, items, category) {
        const checked = this.runnerState.includeSpecs[category];

        const result = [];
        const remaining = [];
        let checkedCount = 0;
        for (const item of items.values()) {
            const value = Math.abs(checked[item.id]);
            if (value === INCLUDE_LEVEL.url) {
                result.push(item);
                checkedCount++;
            } else {
                remaining.push(item);
            }
        }

        const matching = lookup(query, remaining);
        result.push(...matching.slice(0, RESULT_LIMIT));

        return [result, checkedCount, matching.length - RESULT_LIMIT];
    }

    findSuggestions() {
        const { suites, tags, tests } = this.env.runner;
        const pattern = getPattern(this.state.query);
        return {
            suites: this.filterItems(pattern, suites, "suites"),
            tags: this.filterItems(pattern, tags, "tags"),
            tests: this.filterItems(pattern, tests, "tests"),
        };
    }

    focusSearchInput() {
        this.searchInputRef.el?.focus();
    }

    getCategoryCounts() {
        const includeSpecs = this.runnerState.includeSpecs;
        const counts = [];
        for (const category of this.categories) {
            let include = 0;
            let exclude = 0;
            for (const value of $values(includeSpecs[category])) {
                switch (value) {
                    case 1:
                    case 2: {
                        include++;
                        break;
                    }
                    case -1:
                    case -2: {
                        exclude++;
                        break;
                    }
                }
            }
            if (include + exclude) {
                counts.push({ category, tip: `Remove all ${category}`, include, exclude });
            }
        }
        return counts;
    }

    getHasIncludeValue() {
        return $values(this.runnerState.includeSpecs).some((values) =>
            $values(values).some((value) => value > 0)
        );
    }

    getLatestSearches() {
        return storageGet(STORAGE.searches) || [];
    }

    /**
     *
     * @param {(Suite | Test)[]} path
     */
    getShortPath(path) {
        if (path.length <= 3) {
            return path.slice(0, -1);
        } else {
            return [path.at(0), EMPTY_SUITE, path.at(-2)];
        }
    }

    /**
     * @param {Iterable<Suite | Tag>} items
     */
    getTop(items) {
        return [...items].sort((a, b) => b.weight - a.weight).slice(0, 5);
    }

    hasFilters() {
        return Boolean(
            this.state.query.trim() ||
                $values(this.runnerState.includeSpecs).some((values) =>
                    $values(values).some((value) => Math.abs(value) === INCLUDE_LEVEL.url)
                )
        );
    }

    /**
     * @param {number} value
     */
    isReadonly(value) {
        return Math.abs(value) > 1;
    }

    /**
     * @param {unknown} item
     */
    isTag(item) {
        return item instanceof Tag;
    }

    /**
     * @param {SearchCategory} categoryId
     * @param {string} id
     * @param {"exclude" | "include"} value
     */
    onIncludeChange(categoryId, id, value) {
        if (value === "include" || value === "exclude") {
            this.setInclude(categoryId, id, value === "include" ? +1 : -1);
        } else {
            this.setInclude(categoryId, id, 0);
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onKeyDown(ev) {
        /**
         * @param {number} inc
         */
        const navigate = (inc) => {
            ev.preventDefault();
            const elements = [
                this.searchInputRef.el,
                ...this.rootRef.el.querySelectorAll("input[type=radio]:checked:enabled"),
            ];
            let nextIndex = elements.indexOf(getActiveElement(document)) + inc;
            if (nextIndex >= elements.length) {
                nextIndex = 0;
            } else if (nextIndex < -1) {
                nextIndex = -1;
            }
            elements.at(nextIndex).focus();
        };

        switch (ev.key) {
            case "Escape": {
                if (this.state.showDropdown) {
                    ev.preventDefault();
                    this.state.showDropdown = false;
                }
                return;
            }
            case "ArrowDown": {
                return navigate(+1);
            }
            case "ArrowUp": {
                return navigate(-1);
            }
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onRegExpKeyDown(ev) {
        switch (ev.key) {
            case "Enter":
            case " ": {
                ev.preventDefault();
                this.toggleRegExp();
                break;
            }
        }
    }

    onSearchInputChange() {
        if (!this.state.query) {
            return;
        }
        const latestSearches = this.getLatestSearches();
        latestSearches.unshift(this.state.query);
        storageSet(STORAGE.searches, [...new Set(latestSearches)].slice(0, 5));
    }

    /**
     * @param {InputEvent & { currentTarget: HTMLInputElement }} ev
     */
    onSearchInputInput(ev) {
        this.state.query = ev.currentTarget.value;
        this.state.empty = !this.hasFilters();

        this.env.ui.resultsPage = 0;

        this.updateParams(true);
        this.updateSuggestions();
    }

    /**
     * @param {KeyboardEvent & { currentTarget: HTMLInputElement }} ev
     */
    onSearchInputKeyDown(ev) {
        switch (ev.key) {
            case "Backspace": {
                if (ev.currentTarget.selectionStart === 0 && ev.currentTarget.selectionEnd === 0) {
                    this.uncheckLastCategory();
                    this.state.empty = !this.hasFilters();
                }
                break;
            }
            case "r": {
                if (ev.altKey) {
                    this.toggleRegExp();
                }
                break;
            }
        }

        if (this.config.fun) {
            this.verifySecretSequenceStep(ev);
        }
    }

    /**
     * @param {SearchCategory} categoryId
     * @param {string} id
     * @param {number} [value]
     */
    setInclude(categoryId, id, value) {
        if (value) {
            this.runnerState.includeSpecs[categoryId][id] = value;
        } else {
            delete this.runnerState.includeSpecs[categoryId][id];
            if (!this.hasFilters()) {
                this.state.empty = true;
            }
        }

        this.updateParams(false);
    }

    /**
     * @param {string} query
     */
    setQuery(query) {
        this.state.query = query;
        this.state.empty = false;

        this.updateParams(true);
        this.updateSuggestions();
        this.focusSearchInput();
    }

    toggleDebug() {
        this.config.debugTest = !this.config.debugTest;
    }

    toggleRegExp() {
        const query = this.state.query.trim();
        if (this.useRegExp) {
            this.state.query = query.slice(1, -1);
        } else {
            this.state.query = `/${query}/`;
        }
        this.updateParams(true);
        this.updateSuggestions();
    }

    uncheckLastCategory() {
        const checked = this.runnerState.includeSpecs;
        for (const category of [...this.categories].reverse()) {
            let foundItemToUncheck = false;
            for (const [key, value] of $entries(checked[category])) {
                if (this.isReadonly(value)) {
                    continue;
                }
                foundItemToUncheck = true;
                delete checked[category][key];
            }
            if (foundItemToUncheck) {
                this.updateParams();
                return true;
            }
        }
        return false;
    }

    /**
     * @param {boolean} [setUseTextFilter]
     */
    updateParams(setUseTextFilter) {
        if (typeof setUseTextFilter === "boolean") {
            this.useTextFilter = setUseTextFilter;
        }
        if (this.useTextFilter) {
            this.config.filter = this.state.query.trim();
            this.config.suite = [];
            this.config.tag = [];
            this.config.test = [];
        } else {
            this.config.filter = "";
            this.config.suite = formatIncludes(this.runnerState.includeSpecs.suites);
            this.config.tag = formatIncludes(this.runnerState.includeSpecs.tags);
            this.config.test = formatIncludes(this.runnerState.includeSpecs.tests);
        }
    }

    /**
     * @param {SearchCategory} categoryId
     * @param {string} id
     */
    toggleInclude(categoryId, id) {
        const currentValue = this.runnerState.includeSpecs[categoryId][id];
        if (currentValue > 1 || currentValue < -1) {
            return; // readonly
        }
        if (currentValue > 0) {
            this.setInclude(categoryId, id, -1);
        } else if (currentValue < 0) {
            this.setInclude(categoryId, id, 0);
        } else {
            this.setInclude(categoryId, id, +1);
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    verifySecretSequenceStep(ev) {
        this.secretSequence ||= 0;
        if (ev.keyCode === SECRET_SEQUENCE[this.secretSequence]) {
            ev.stopPropagation();
            ev.preventDefault();
            this.secretSequence++;
        } else {
            this.secretSequence = 0;
            return;
        }

        if (this.secretSequence === SECRET_SEQUENCE.length) {
            this.secretSequence = 0;

            const { runner } = this.env;
            runner.stop();
            runner.reporting.passed += runner.reporting.failed;
            runner.reporting.passed += runner.reporting.todo;
            runner.reporting.failed = 0;
            runner.reporting.todo = 0;
            for (const [, suite] of runner.suites) {
                suite.reporting.passed += suite.reporting.failed;
                suite.reporting.passed += suite.reporting.todo;
                suite.reporting.failed = 0;
                suite.reporting.todo = 0;
            }
            for (const [, test] of runner.tests) {
                test.config.todo = false;
                test.status = Test.PASSED;
                for (const result of test.results) {
                    result.pass = true;
                    result.errors = [];
                    for (const assertion of result.assertions) {
                        assertion.pass = true;
                    }
                }
            }
            this.__owl__.app.root.render(true);
            console.warn("Secret sequence activated: all tests pass!");
        }
    }
}
