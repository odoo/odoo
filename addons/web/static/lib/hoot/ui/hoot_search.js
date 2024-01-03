/** @odoo-module */

import { Component, useRef, useState, xml } from "@odoo/owl";
import { getActiveElement } from "@web/../lib/hoot-dom/helpers/dom";
import { isRegExpFilter, parseRegExp } from "@web/../lib/hoot-dom/hoot_dom_utils";
import { Suite } from "../core/suite";
import { Tag } from "../core/tag";
import { EXCLUDE_PREFIX, refresh, setParams, subscribeToURLParams } from "../core/url";
import { debounce, lookup, normalize, title, useWindowListener } from "../hoot_utils";
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

const { document, Object } = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 *
 * @param {Record<string, boolean>} values
 */
const formatIncludes = (values) =>
    Object.entries(values).map(([id, value]) => (value ? id : `${EXCLUDE_PREFIX}${id}`));

/**
 * @param {string} query
 */
const getPattern = (query) => {
    query = query.match(R_QUERY_CONTENT)[1];
    return parseRegExp(normalize(query));
};

const EMPTY_SUITE = new Suite(null, "...", []);
const R_QUERY_CONTENT = new RegExp(`^\\s*${EXCLUDE_PREFIX}?\\s*(.*)\\s*$`);

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
                            t-att-checked="urlParams.debugTest"
                            t-att-disabled="isRunning"
                            t-on-change="toggleDebug"
                        />
                        <i class="fa fa-bug text-muted transition-colors" />
                    </label>
                </div>
                <t t-if="state.showDropdown">
                    <div class="hoot-search-dropdown animate-slide-down bg-base text-base absolute mt-1 px-2 py-3 shadow rounded shadow z-10">
                        <div class="flex mb-2">
                            <t t-if="state.query.trim()">
                                <button
                                    class="flex items-center gap-1"
                                    type="submit"
                                    title="Run this filter"
                                    t-on-pointerdown="() => this.updateParams(true)"
                                >
                                    <h6 class="text-primary text-sm m-0">
                                        Filter using
                                        <t t-if="useRegExp">
                                            regular expression
                                        </t>
                                        <t t-else="">
                                            text
                                        </t>
                                    </h6>
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
                            <t t-if="state.categories[category].length">
                                <div class="flex flex-col mb-2">
                                    <h6 class="text-primary text-sm font-bold flex items-center mb-2">
                                        <span class="w-full">
                                            <t t-esc="title(category)" />
                                            (<t t-esc="state.categories[category].length" />)
                                        </span>
                                    </h6>
                                    <ul class="flex flex-col overflow-y-auto gap-1">
                                        <t t-foreach="state.categories[category]" t-as="job" t-key="job.id">
                                            <t t-set="checked" t-value="runnerState.includeSpecs[category]" />
                                            <li
                                                class="flex items-center gap-1 cursor-pointer select-none"
                                                t-on-click="() => this.toggleInclude(category, job.id)"
                                            >
                                                <div
                                                    class="hoot-include-widget h-5 p-px flex items-center relative border border-primary rounded-full"
                                                    t-on-click.stop=""
                                                    t-on-change="(ev) => this.onIncludeChange(category, job.id, ev.target.value)"
                                                >
                                                    <input
                                                        type="radio"
                                                        class="w-4 h-4 cursor-pointer appearance-none"
                                                        title="Exclude"
                                                        t-att-name="job.id" value="exclude"
                                                        t-att-checked="checked[job.id] === false"
                                                    />
                                                    <input
                                                        type="radio"
                                                        class="w-4 h-4 cursor-pointer appearance-none"
                                                        t-att-name="job.id" value="null"
                                                        t-att-checked="![true, false].includes(checked[job.id])"
                                                    />
                                                    <input
                                                        type="radio"
                                                        class="w-4 h-4 cursor-pointer appearance-none"
                                                        title="Include"
                                                        t-att-name="job.id" value="include"
                                                        t-att-checked="checked[job.id] === true"
                                                    />
                                                </div>
                                                <t t-if="isTag(job)">
                                                    <HootTagButton tag="job" disabled="true" />
                                                </t>
                                                <t t-else="">
                                                    <span class="hoot-path flex items-center font-bold whitespace-nowrap overflow-hidden" t-att-title="job.fullName">
                                                        <t t-foreach="getShortPath(job.path)" t-as="suite" t-key="suite.id">
                                                            <span class="text-muted px-1" t-esc="suite.name" />
                                                            <span class="font-normal">/</span>
                                                        </t>
                                                        <t t-set="isSet" t-value="job.id in checked" />
                                                        <span
                                                            class="truncate px-1"
                                                            t-att-class="{
                                                                'font-extrabold': isSet,
                                                                'text-pass': checked[job.id] === true,
                                                                'text-fail': checked[job.id] === false,
                                                                'text-muted': !isSet and hasIncludeValue,
                                                                'text-primary': !isSet and !hasIncludeValue,
                                                                'fst-italic': hasIncludeValue ? !checked[job.id] : checked[job.id] === false,
                                                            }"
                                                            t-esc="job.name"
                                                        />
                                                    </span>
                                                </t>
                                            </li>
                                        </t>
                                    </ul>
                                </div>
                            </t>
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
        return this.useRegExp ? query : `"${query}"`;
    }

    updateSuggestions = debounce(() => {
        this.state.categories = this.findSuggestions();
        this.state.showDropdown = true;
    }, 16);

    setup() {
        const { runner } = this.env;

        runner.beforeAll(() => {
            this.state.categories = this.findSuggestions();
        });
        runner.afterAll(() => {
            this.searchInputRef.el?.focus();
        });

        this.rootRef = useRef("root");
        this.searchInputRef = useRef("search-input");
        this.urlParams = subscribeToURLParams("debugTest");
        this.state = useState({
            query: this.urlParams.filter || "",
            disabled: false,
            showDropdown: false,
            categories: {
                /** @type {Suite[]} */
                suites: [],
                /** @type {Tag[]} */
                tags: [],
                /** @type {Test[]} */
                tests: [],
            },
        });
        this.runnerState = useState(runner.state);

        useWindowListener("click", this.onWindowClick);
    }

    /**
     * @param {string} query
     * @param {Iterable<Suite | Tag | Test>} items
     * @param {SearchCategory} category
     */
    filterItems(query, items, category) {
        const checked = this.runnerState.includeSpecs[category];

        const result = [];
        const remaining = [];
        for (const item of items) {
            if (item.id in checked) {
                result.push(item);
            } else {
                remaining.push(item);
            }
        }

        const matching = lookup(query, remaining, (item) => item.key);
        result.push(...matching.slice(0, 5));

        return result;
    }

    findSuggestions() {
        const { suites, tags, tests } = this.env.runner;
        const pattern = getPattern(this.state.query);
        return {
            suites: this.filterItems(pattern, suites.values(), "suites"),
            tags: this.filterItems(pattern, tags, "tags"),
            tests: this.filterItems(pattern, tests.values(), "tests"),
        };
    }

    getCategoryCounts() {
        const checked = this.runnerState.includeSpecs;
        const counts = [];
        for (const category of this.categories) {
            let include = 0;
            let exclude = 0;
            for (const value of Object.values(checked[category])) {
                if (value === true) {
                    include++;
                } else if (value === false) {
                    exclude++;
                }
            }
            if (include + exclude) {
                counts.push({ category, tip: `Remove all ${category}`, include, exclude });
            }
        }
        return counts;
    }

    getHasIncludeValue() {
        return Object.values(this.runnerState.includeSpecs).some((values) =>
            Object.values(values).includes(true)
        );
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
     * @param {unknown} item
     */
    isTag(item) {
        return item instanceof Tag;
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onDebugKeyDown(ev) {
        switch (ev.key) {
            case "Enter":
            case " ": {
                ev.preventDefault();
                this.toggleDebug();
                break;
            }
        }
    }

    /**
     * @param {SearchCategory} categoryId
     * @param {string} id
     * @param {"exclude" | "include"} value
     */
    onIncludeChange(categoryId, id, value) {
        if (value === "include" || value === "exclude") {
            this.setInclude(categoryId, id, value === "include");
        } else {
            this.setInclude(categoryId, id, null);
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
                ...this.rootRef.el.querySelectorAll("input[type=radio]:checked"),
            ];
            let nextIndex = elements.indexOf(getActiveElement()) + inc;
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

    /**
     * @param {InputEvent} ev
     */
    onSearchInputInput(ev) {
        this.state.query = ev.target.value;

        this.updateParams(true);
        this.updateSuggestions();
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onSearchInputKeyDown(ev) {
        switch (ev.key) {
            case "Backspace": {
                if (ev.target.selectionStart === 0 && ev.target.selectionEnd === 0) {
                    this.uncheckLastCategory();
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
    }

    /**
     * @param {PointerEvent} ev
     */
    onWindowClick(ev) {
        if (this.runnerState.status !== "running") {
            this.state.showDropdown = ev.composedPath().includes(this.rootRef.el);
        }
    }

    /**
     * @param {SearchCategory} categoryId
     * @param {string} id
     * @param {boolean | null} [value]
     */
    setInclude(categoryId, id, value) {
        if (typeof value === "boolean") {
            this.runnerState.includeSpecs[categoryId][id] = value;
        } else {
            delete this.runnerState.includeSpecs[categoryId][id];
        }

        this.updateParams(false);
    }

    toggleDebug() {
        setParams({ debugTest: !this.urlParams.debugTest });
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
            if (Object.keys(checked[category]).length) {
                checked[category] = {};
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
            setParams({
                filter: this.state.query.trim(),
                suite: null,
                tag: null,
                test: null,
            });
        } else {
            setParams({
                filter: null,
                suite: formatIncludes(this.runnerState.includeSpecs.suites),
                tag: formatIncludes(this.runnerState.includeSpecs.tags),
                test: formatIncludes(this.runnerState.includeSpecs.tests),
            });
        }
    }

    /**
     * @param {SearchCategory} categoryId
     * @param {string} id
     */
    toggleInclude(categoryId, id) {
        const currentValue = this.runnerState.includeSpecs[categoryId][id];
        if (currentValue === true) {
            this.setInclude(categoryId, id, false);
        } else if (currentValue === false) {
            this.setInclude(categoryId, id, null);
        } else {
            this.setInclude(categoryId, id, true);
        }
    }
}
