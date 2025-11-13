/** @odoo-module */

import { Component, onPatched, onWillPatch, useRef, useState, xml } from "@odoo/owl";
import { getActiveElement } from "@web/../lib/hoot-dom/helpers/dom";
import { R_REGEX, REGEX_MARKER } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { Suite } from "../core/suite";
import { Tag } from "../core/tag";
import { Test } from "../core/test";
import { refresh } from "../core/url";
import {
    debounce,
    EXACT_MARKER,
    INCLUDE_LEVEL,
    lookup,
    parseQuery,
    R_QUERY_EXACT,
    STORAGE,
    storageGet,
    storageSet,
    stringify,
    title,
    useHootKey,
    useWindowListener,
} from "../hoot_utils";
import { HootTagButton } from "./hoot_tag_button";

/**
 * @typedef {{
 * }} HootSearchProps
 *
 * @typedef {import("../core/config").SearchFilter} SearchFilter
 *
 * @typedef {import("../core/tag").Tag} Tag
 *
 * @typedef {import("../core/test").Test} Test
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    Math: { abs: $abs },
    Object: { entries: $entries, values: $values },
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {string} query
 */
function addExact(query) {
    return EXACT_MARKER + query + EXACT_MARKER;
}

/**
 * @param {string} query
 */
function addRegExp(query) {
    return REGEX_MARKER + query + REGEX_MARKER;
}

/**
 * @param {"suite" | "tag" | "test"} category
 */
function categoryToType(category) {
    return category === "tag" ? category : "id";
}

/**
 * @param {string} query
 */
function removeExact(query) {
    return query.replaceAll(EXACT_MARKER, "");
}

/**
 * @param {string} query
 */
function removeRegExp(query) {
    return query.slice(1, -1);
}

/**
 * /!\ Requires "job" and "category" to be in scope
 *
 * @param {string} tagName
 */
const templateIncludeWidget = (tagName) => /* xml */ `
    <t t-set="type" t-value="category === 'tag' ? category : 'id'" />
    <t t-set="includeStatus" t-value="runnerState.includeSpecs[type][job.id] or 0" />
    <t t-set="readonly" t-value="isReadonly(includeStatus)" />

    <${tagName}
        class="flex items-center gap-1 cursor-pointer select-none"
        t-on-click.stop="() => this.toggleInclude(type, job.id)"
    >
        <div
            class="hoot-include-widget h-5 p-px flex items-center relative border rounded-full"
            t-att-class="{
                'border-gray': readonly,
                'border-primary': !readonly,
                'opacity-50': readonly,
            }"
            t-att-title="readonly and 'Cannot change because it depends on a tag modifier in the code'"
            t-on-pointerup="focusSearchInput"
            t-on-change="(ev) => this.onIncludeChange(type, job.id, ev.target.value)"
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
                    <span class="text-gray px-1" t-esc="suite.name" />
                    <span class="font-normal">/</span>
                </t>
                <t t-set="isSet" t-value="job.id in runnerState.includeSpecs.id" />
                <span
                    class="truncate px-1"
                    t-att-class="{
                        'font-extrabold': isSet,
                        'text-emerald': includeStatus gt 0,
                        'text-rose': includeStatus lt 0,
                        'text-gray': !isSet and hasIncludeValue,
                        'text-primary': !isSet and !hasIncludeValue,
                        'italic': hasIncludeValue ? includeStatus lte 0 : includeStatus lt 0,
                    }"
                    t-esc="job.name"
                />
            </span>
        </t>
    </${tagName}>
`;

/**
 *
 * @param {ReturnType<typeof useRef<HTMLInputElement>>} ref
 */
function useKeepSelection(ref) {
    /**
     * @param {number} nextOffset
     */
    function keepSelection(nextOffset) {
        offset = nextOffset || 0;
    }

    let offset = null;
    let start = 0;
    let end = 0;
    onWillPatch(() => {
        if (offset === null || !ref.el) {
            return;
        }
        start = ref.el.selectionStart;
        end = ref.el.selectionEnd;
    });
    onPatched(() => {
        if (offset === null || !ref.el) {
            return;
        }
        ref.el.selectionStart = start + offset;
        ref.el.selectionEnd = end + offset;
        offset = null;
    });

    return keepSelection;
}

const EMPTY_SUITE = new Suite(null, "…", []);
const SECRET_SEQUENCE = [38, 38, 40, 40, 37, 39, 37, 39, 66, 65];
const RESULT_LIMIT = 5;

// Template parts, because 16 levels of indent is a bit much

const TEMPLATE_FILTERS_AND_CATEGORIES = /* xml */ `
    <div class="flex mb-2">
        <t t-if="trimmedQuery">
            <button
                class="flex items-center gap-1"
                type="submit"
                title="Run this filter"
                t-on-pointerdown="updateFilterParam"
            >
                <h4 class="text-primary m-0">
                    Filter using
                    <t t-if="hasRegExpFilter()">
                        regular expression
                    </t>
                    <t t-else="">
                        text
                    </t>
                </h4>
                <t t-esc="wrappedQuery()" />
            </button>
        </t>
        <t t-else="">
            <em class="text-gray ms-1">
                Start typing to show filters...
            </em>
        </t>
    </div>
    <t t-foreach="categories" t-as="category" t-key="category">
        <t t-set="jobs" t-value="state.categories[category][0]" />
        <t t-set="remainingCount" t-value="state.categories[category][1]" />
        <t t-if="jobs?.length">
            <div class="flex flex-col mb-2 max-h-48 overflow-hidden">
                <h4
                    class="text-primary font-bold flex items-center mb-2"
                    t-esc="title(category)"
                />
                <ul class="flex flex-col overflow-y-auto gap-1">
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
        <div class="flex flex-col sm:px-4 border-gray sm:border-x">
            <h4 class="text-primary font-bold flex items-center mb-2">
                <span class="w-full">
                    Available suites
                </span>
            </h4>
            <ul class="flex flex-col overflow-y-auto gap-1">
                <t t-foreach="getTop(env.runner.rootSuites)" t-as="job" t-key="job.id">
                    <t t-set="category" t-value="'suite'" />
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
                    <t t-set="category" t-value="'tag'" />
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
        <search class="${HootSearch.name} flex-1" t-ref="root" t-on-keydown="onKeyDown">
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
                                <t t-if="count.include.length">
                                    <span class="text-emerald" t-esc="count.include.length" />
                                </t>
                                <t t-if="count.exclude.length">
                                    <span class="text-rose" t-esc="count.exclude.length" />
                                </t>
                            </span>
                        </button>
                    </t>
                    <input
                        type="search"
                        class="w-full rounded p-1 outline-none"
                        t-att-autofocus="!config.manual"
                        placeholder="Filter suites, tests or tags"
                        t-ref="search-input"
                        t-att-class="{ 'text-gray': !config.filter }"
                        t-att-disabled="isRunning"
                        t-att-value="state.query"
                        t-on-change="onSearchInputChange"
                        t-on-input="onSearchInputInput"
                        t-on-keydown="onSearchInputKeyDown"
                    />
                    <label
                        class="hoot-search-icon cursor-pointer p-1"
                        title="Use exact match (Alt + X)"
                        tabindex="0"
                        t-on-keydown="onExactKeyDown"
                    >
                        <input
                            type="checkbox"
                            class="hidden"
                            t-att-checked="hasExactFilter()"
                            t-att-disabled="isRunning"
                            t-on-change="toggleExact"
                        />
                        <i class="fa fa-quote-right text-gray transition-colors" />
                    </label>
                    <label
                        class="hoot-search-icon cursor-pointer p-1"
                        title="Use regular expression (Alt + R)"
                        tabindex="0"
                        t-on-keydown="onRegExpKeyDown"
                    >
                        <input
                            type="checkbox"
                            class="hidden"
                            t-att-checked="hasRegExpFilter()"
                            t-att-disabled="isRunning"
                            t-on-change="toggleRegExp"
                        />
                        <i class="fa fa-asterisk text-gray transition-colors" />
                    </label>
                    <label
                        class="hoot-search-icon cursor-pointer p-1"
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
                        <i class="fa fa-bug text-gray transition-colors" />
                    </label>
                </div>
                <t t-if="state.showDropdown">
                    <div class="hoot-dropdown-lg flex flex-col animate-slide-down bg-base text-base absolute mt-1 p-3 shadow rounded z-2">
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

    categories = ["suite", "test", "tag"];
    debouncedUpdateSuggestions = debounce(this.updateSuggestions.bind(this), 16);
    refresh = refresh;
    title = title;

    get trimmedQuery() {
        return this.state.query.trim();
    }

    setup() {
        const { runner } = this.env;

        runner.beforeAll(() => {
            this.state.categories = this.findSuggestions();
            this.state.empty = this.isEmpty();
        });
        runner.afterAll(() => this.focusSearchInput());

        this.rootRef = useRef("root");
        this.searchInputRef = useRef("search-input");

        this.config = useState(runner.config);
        const query = this.config.filter || "";
        this.state = useState({
            categories: {
                /** @type {Suite[]} */
                suite: [],
                /** @type {Tag[]} */
                tag: [],
                /** @type {Test[]} */
                test: [],
            },
            disabled: false,
            empty: !query.trim(),
            query,
            showDropdown: false,
        });
        this.runnerState = useState(runner.state);

        useHootKey(["Alt", "r"], this.toggleRegExp);
        useHootKey(["Alt", "x"], this.toggleExact);
        useHootKey(["Escape"], this.closeDropdown);

        useWindowListener(
            "click",
            (ev) => {
                if (this.runnerState.status !== "running") {
                    const shouldOpen = ev.composedPath().includes(this.rootRef.el);
                    if (shouldOpen && !this.state.showDropdown) {
                        this.debouncedUpdateSuggestions();
                    }
                    this.state.showDropdown = shouldOpen;
                }
            },
            { capture: true }
        );

        this.keepSelection = useKeepSelection(this.searchInputRef);
    }

    /**
     * @param {KeyboardEvent} ev
     */
    closeDropdown(ev) {
        if (!this.state.showDropdown) {
            return;
        }
        ev.preventDefault();
        this.state.showDropdown = false;
    }

    /**
     * @param {string} parsedQuery
     * @param {Map<string, Suite | Tag | Test>} items
     * @param {SearchFilter} category
     */
    filterItems(parsedQuery, items, category) {
        const checked = this.runnerState.includeSpecs[category];

        const result = [];
        const remaining = [];
        for (const item of items.values()) {
            const value = $abs(checked[item.id]);
            if (value === INCLUDE_LEVEL.url) {
                result.push(item);
            } else {
                remaining.push(item);
            }
        }

        const matching = lookup(parsedQuery, remaining);
        result.push(...matching.slice(0, RESULT_LIMIT));

        return [result, matching.length - RESULT_LIMIT];
    }

    findSuggestions() {
        const { suites, tags, tests } = this.env.runner;
        const parsedQuery = parseQuery(this.trimmedQuery);
        return {
            suite: this.filterItems(parsedQuery, suites, "id"),
            tag: this.filterItems(parsedQuery, tags, "tag"),
            test: this.filterItems(parsedQuery, tests, "id"),
        };
    }

    focusSearchInput() {
        this.searchInputRef.el?.focus();
    }

    getCategoryCounts() {
        const { includeSpecs } = this.runnerState;
        const { suites, tests } = this.env.runner;
        const counts = [];
        for (const category of this.categories) {
            const include = [];
            const exclude = [];
            for (const [id, value] of $entries(includeSpecs[categoryToType(category)])) {
                if (
                    (category === "suite" && !suites.has(id)) ||
                    (category === "test" && !tests.has(id))
                ) {
                    continue;
                }
                switch (value) {
                    case +INCLUDE_LEVEL.url:
                    case +INCLUDE_LEVEL.tag: {
                        include.push(id);
                        break;
                    }
                    case -INCLUDE_LEVEL.url:
                    case -INCLUDE_LEVEL.tag: {
                        exclude.push(id);
                        break;
                    }
                }
            }
            if (include.length || exclude.length) {
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

    hasExactFilter(query = this.trimmedQuery) {
        R_QUERY_EXACT.lastIndex = 0;
        return R_QUERY_EXACT.test(query);
    }

    hasRegExpFilter(query = this.trimmedQuery) {
        return R_REGEX.test(query);
    }

    isEmpty() {
        return !(
            this.trimmedQuery ||
            $values(this.runnerState.includeSpecs).some((values) =>
                $values(values).some((value) => $abs(value) === INCLUDE_LEVEL.url)
            )
        );
    }

    /**
     * @param {number} value
     */
    isReadonly(value) {
        return $abs(value) > INCLUDE_LEVEL.url;
    }

    /**
     * @param {unknown} item
     */
    isTag(item) {
        return item instanceof Tag;
    }
    /**
     * @param {number} inc
     */
    navigate(inc) {
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
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onExactKeyDown(ev) {
        switch (ev.key) {
            case "Enter":
            case " ": {
                this.toggleExact(ev);
                break;
            }
        }
    }

    /**
     * @param {SearchFilter} type
     * @param {string} id
     * @param {"exclude" | "include"} value
     */
    onIncludeChange(type, id, value) {
        if (value === "include" || value === "exclude") {
            this.setInclude(
                type,
                id,
                value === "include" ? +INCLUDE_LEVEL.url : -INCLUDE_LEVEL.url
            );
        } else {
            this.setInclude(type, id, 0);
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onKeyDown(ev) {
        switch (ev.key) {
            case "ArrowDown": {
                ev.preventDefault();
                return this.navigate(+1);
            }
            case "ArrowUp": {
                ev.preventDefault();
                return this.navigate(-1);
            }
            case "Enter": {
                return refresh();
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
                this.toggleRegExp(ev);
                break;
            }
        }
    }

    onSearchInputChange() {
        if (!this.trimmedQuery) {
            return;
        }
        const latestSearches = this.getLatestSearches();
        latestSearches.unshift(this.trimmedQuery);
        storageSet(STORAGE.searches, [...new Set(latestSearches)].slice(0, 5));
    }

    /**
     * @param {InputEvent & { currentTarget: HTMLInputElement }} ev
     */
    onSearchInputInput(ev) {
        this.state.query = ev.currentTarget.value;

        this.env.ui.resultsPage = 0;

        this.updateFilterParam();
        this.debouncedUpdateSuggestions();
    }

    /**
     * @param {KeyboardEvent & { currentTarget: HTMLInputElement }} ev
     */
    onSearchInputKeyDown(ev) {
        switch (ev.key) {
            case "Backspace": {
                if (ev.currentTarget.selectionStart === 0 && ev.currentTarget.selectionEnd === 0) {
                    this.uncheckLastCategory();
                }
                break;
            }
        }

        if (this.config.fun) {
            this.verifySecretSequenceStep(ev);
        }
    }

    /**
     * @param {SearchFilter} type
     * @param {string} id
     * @param {number} [value]
     */
    setInclude(type, id, value) {
        this.config.filter = "";
        this.env.runner.include(type, id, value);
    }

    /**
     * @param {string} query
     */
    setQuery(query) {
        this.state.query = query;

        this.updateFilterParam();
        this.updateSuggestions();
        this.focusSearchInput();
    }

    toggleDebug() {
        this.config.debugTest = !this.config.debugTest;
    }

    /**
     * @param {Event} ev
     */
    toggleExact(ev) {
        ev.preventDefault();

        const currentQuery = this.trimmedQuery;
        let query = currentQuery;
        if (this.hasRegExpFilter(query)) {
            query = removeRegExp(query);
        }
        if (this.hasExactFilter(query)) {
            query = removeExact(query);
        } else {
            query = addExact(query);
        }
        this.keepSelection((query.length - currentQuery.length) / 2);
        this.setQuery(query);
    }

    /**
     * @param {SearchFilter} type
     * @param {string} id
     */
    toggleInclude(type, id) {
        const currentValue = this.runnerState.includeSpecs[type][id];
        if (this.isReadonly(currentValue)) {
            return; // readonly
        }
        if (currentValue > 0) {
            this.setInclude(type, id, -INCLUDE_LEVEL.url);
        } else if (currentValue < 0) {
            this.setInclude(type, id, 0);
        } else {
            this.setInclude(type, id, +INCLUDE_LEVEL.url);
        }
    }

    /**
     * @param {Event} ev
     */
    toggleRegExp(ev) {
        ev.preventDefault();

        const currentQuery = this.trimmedQuery;
        let query = currentQuery;
        if (this.hasExactFilter(query)) {
            query = removeExact(query);
        }
        if (this.hasRegExpFilter(query)) {
            query = removeRegExp(query);
        } else {
            query = addRegExp(query);
        }
        this.keepSelection((query.length - currentQuery.length) / 2);
        this.setQuery(query);
    }

    uncheckLastCategory() {
        for (const count of this.getCategoryCounts().reverse()) {
            const type = categoryToType(count.category);
            const includeSpecs = this.runnerState.includeSpecs[type];
            for (const id of [...count.exclude, ...count.include]) {
                const value = includeSpecs[id];
                if (this.isReadonly(value)) {
                    continue;
                }
                this.setInclude(type, id, 0);
                return true;
            }
        }
        return false;
    }

    updateFilterParam() {
        this.config.filter = this.trimmedQuery;
    }

    updateSuggestions() {
        this.state.empty = this.isEmpty();
        this.state.categories = this.findSuggestions();
        this.state.showDropdown = true;
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
                    result.currentErrors = [];
                    for (const assertion of result.getEvents("assertion")) {
                        assertion.pass = true;
                    }
                }
            }
            this.__owl__.app.root.render(true);
            console.warn("Secret sequence activated: all tests pass!");
        }
    }

    wrappedQuery(query = this.trimmedQuery) {
        return this.hasRegExpFilter(query) ? query : stringify(query);
    }
}
