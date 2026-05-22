/** @odoo-module */

import {
    Component,
    computed,
    onPatched,
    onWillPatch,
    plugin,
    signal,
    types as t,
    xml,
} from "@odoo/owl";
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
import { getConfigPlugin, getRunnerPlugin } from "./runner_plugin";
import { UiPlugin } from "./ui_plugin";

/**
 * @typedef {import("../core/config").SearchFilter} SearchFilter
 * @typedef {import("../core/tag").Tag} Tag
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
    <t t-set="includeStatus" t-value="this.runner.includeSpecs[type][job.id] or 0" />
    <t t-set="readonly" t-value="this.isReadonly(includeStatus)" />

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
            t-on-pointerup="this.focusSearchInput"
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
        <t t-if="this.isTag(job)">
            <HootTagButton tag="job" inert="true" />
        </t>
        <t t-else="">
            <span
                class="flex items-center font-bold whitespace-nowrap overflow-hidden"
                t-att-title="job.fullName"
            >
                <t t-foreach="this.getShortPath(job.path)" t-as="suite" t-key="suite.id">
                    <span class="text-gray px-1" t-out="suite.name" />
                    <span class="font-normal">/</span>
                </t>
                <t t-set="isSet" t-value="job.id in this.runner.includeSpecs.id" />
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
                    t-out="job.name"
                />
            </span>
        </t>
    </${tagName}>
`;

/**
 *
 * @param {typeof t.ref<HTMLElement>} ref
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
        if (offset === null || !ref()) {
            return;
        }
        start = ref().selectionStart;
        end = ref().selectionEnd;
    });
    onPatched(() => {
        if (offset === null || !ref()) {
            return;
        }
        ref().selectionStart = start + offset;
        ref().selectionEnd = end + offset;
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
        <t t-if="this.trimmedQuery()">
            <button
                class="flex items-center gap-1"
                type="submit"
                title="Run this filter"
                t-on-pointerdown="this.updateFilterParam"
            >
                <h4 class="text-primary m-0">
                    Filter using
                    <t t-if="this.hasRegExpFilter(this.trimmedQuery())">
                        regular expression
                    </t>
                    <t t-else="">
                        text
                    </t>
                </h4>
                <t t-out="this.wrappedQuery(this.trimmedQuery())" />
            </button>
        </t>
        <t t-else="">
            <em class="text-gray ms-1">
                Start typing to show filters...
            </em>
        </t>
    </div>
    <t t-foreach="this.categoryKeys" t-as="category" t-key="category">
        <t t-set="jobs" t-value="this.categories[category]()[0]" />
        <t t-set="remainingCount" t-value="this.categories[category]()[1]" />
        <t t-if="jobs?.length">
            <div class="flex flex-col mb-2 max-h-48 overflow-hidden">
                <h4
                    class="text-primary font-bold flex items-center mb-2"
                    t-out="this.title(category)"
                />
                <ul class="flex flex-col overflow-y-auto gap-1">
                    <t t-foreach="jobs" t-as="job" t-key="job.id">
                        ${templateIncludeWidget("li")}
                    </t>
                    <t t-if="remainingCount > 0">
                        <div class="italic">
                            <t t-out="remainingCount" /> more items ...
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
                <t t-foreach="this.getLatestSearches()" t-as="text" t-key="text_index">
                    <li>
                        <button
                            class="w-full px-2 hover:bg-gray-300 dark:hover:bg-gray-700"
                            type="button"
                            t-on-click.stop="() => this.setQuery(text)"
                            t-out="text"
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
                <t t-foreach="this.getTop(this.runner.rootSuites)" t-as="job" t-key="job.id">
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
                <t t-foreach="this.getTop(this.runner.tags.values())" t-as="job" t-key="job.id">
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

export class HootSearch extends Component {
    static components = { HootTagButton };
    static template = xml`
        <t t-set="hasIncludeValue" t-value="this.getHasIncludeValue()" />
        <t t-set="isRunning" t-value="this.runner.status() === 'running'" />
        <search class="${HootSearch.name} flex-1" t-ref="this.rootRef" t-on-keydown="this.onKeyDown">
            <form class="relative" t-on-submit.prevent="this.refresh">
                <div class="hoot-search-bar flex border rounded items-center bg-base px-1 gap-1 w-full transition-colors">
                    <t t-foreach="this.getCategoryCounts()" t-as="count" t-key="count.category">
                        <button
                            type="button"
                            class="flex border border-primary rounded"
                            t-att-title="count.tip"
                        >
                            <span class="bg-btn px-1 transition-colors" t-out="count.category" />
                            <span class="mx-1 flex gap-1">
                                <t t-if="count.include.length">
                                    <span class="text-emerald" t-out="count.include.length" />
                                </t>
                                <t t-if="count.exclude.length">
                                    <span class="text-rose" t-out="count.exclude.length" />
                                </t>
                            </span>
                        </button>
                    </t>
                    <input
                        type="search"
                        class="w-full rounded p-1 outline-none"
                        t-att-autofocus="!this.config.manual()"
                        placeholder="Filter suites, tests or tags"
                        t-ref="this.searchInputRef"
                        t-att-class="{ 'text-gray': !this.config.filter() }"
                        t-att-disabled="isRunning"
                        t-att-value="this.query()"
                        t-on-change="this.onSearchInputChange"
                        t-on-input="this.onSearchInputInput"
                        t-on-keydown="this.onSearchInputKeyDown"
                    />
                    <label
                        class="hoot-search-icon cursor-pointer p-1"
                        title="Use exact match (Alt + X)"
                        tabindex="0"
                        t-on-keydown="this.onExactKeyDown"
                    >
                        <input
                            type="checkbox"
                            class="hidden"
                            t-att-checked="this.hasExactFilter(this.trimmedQuery())"
                            t-att-disabled="isRunning"
                            t-on-change="this.toggleExact"
                        />
                        <i class="fa fa-quote-right text-gray transition-colors" />
                    </label>
                    <label
                        class="hoot-search-icon cursor-pointer p-1"
                        title="Use regular expression (Alt + R)"
                        tabindex="0"
                        t-on-keydown="this.onRegExpKeyDown"
                    >
                        <input
                            type="checkbox"
                            class="hidden"
                            t-att-checked="this.hasRegExpFilter(this.trimmedQuery())"
                            t-att-disabled="isRunning"
                            t-on-change="this.toggleRegExp"
                        />
                        <i class="fa fa-asterisk text-gray transition-colors" />
                    </label>
                    <label
                        class="hoot-search-icon cursor-pointer p-1"
                        title="Debug mode (Alt + D)"
                        t-on-keydown="this.onDebugKeyDown"
                    >
                        <input
                            type="checkbox"
                            class="hidden"
                            t-att-checked="this.config.debugTest()"
                            t-att-disabled="isRunning"
                            t-on-change="this.toggleDebug"
                        />
                        <i class="fa fa-bug text-gray transition-colors" />
                    </label>
                </div>
                <t t-if="this.showDropdown()">
                    <div class="hoot-dropdown-lg flex flex-col animate-slide-down bg-base text-base absolute mt-1 p-3 shadow rounded z-2">
                        <t t-if="this.isEmpty()">
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

    // Props & plugins
    config = getConfigPlugin();
    runner = getRunnerPlugin();
    ui = plugin(UiPlugin);

    // Reactive values
    rootRef = signal(null, { type: t.ref(HTMLElement) });
    searchInputRef = signal(null, { type: t.ref(HTMLInputElement) });
    categories = {
        suite: signal.Array([], { type: t.instanceOf(Suite) }),
        tag: signal.Array([], { type: t.instanceOf(Tag) }),
        test: signal.Array([], { type: t.instanceOf(Test) }),
    };
    query = signal(this.config.filter() || "", { type: t.string() });
    isEmpty = signal(!this.query().trim(), { type: t.string() });
    showDropdown = signal(false, { type: t.boolean() });
    trimmedQuery = computed(() => this.query().trim());

    // Other members
    categoryKeys = Object.keys(this.categories);
    debouncedUpdateSuggestions = debounce(this.updateSuggestions.bind(this), 16);
    keepSelection = useKeepSelection(this.searchInputRef);
    refresh = refresh;
    title = title;

    setup() {
        this.runner.beforeAll(() => {
            this.updateSuggestedCategories();
            this.isEmpty.set(this.computeIsEmpty());
        });
        this.runner.afterAll(() => this.focusSearchInput());

        useHootKey(["Alt", "r"], this.toggleRegExp.bind(this));
        useHootKey(["Alt", "x"], this.toggleExact.bind(this));
        useHootKey(["Escape"], this.closeDropdown.bind(this));

        useWindowListener(
            "click",
            (ev) => {
                if (this.runner.status() !== "running") {
                    const shouldOpen = ev.composedPath().includes(this.rootRef());
                    if (shouldOpen && !this.showDropdown()) {
                        this.debouncedUpdateSuggestions();
                    }
                    this.showDropdown.set(shouldOpen);
                }
            },
            { capture: true }
        );
    }

    /**
     * @param {KeyboardEvent} ev
     */
    closeDropdown(ev) {
        if (!this.showDropdown()) {
            return;
        }
        ev.preventDefault();
        this.showDropdown.set(false);
    }

    computeIsEmpty() {
        return !(
            this.trimmedQuery() ||
            $values(this.runner.includeSpecs).some((values) =>
                $values(values).some((value) => $abs(value) === INCLUDE_LEVEL.url)
            )
        );
    }

    /**
     * @param {string} parsedQuery
     * @param {Map<string, Suite | Tag | Test>} items
     * @param {SearchFilter} category
     */
    filterItems(parsedQuery, items, category) {
        const checked = this.runner.includeSpecs[category];

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

    updateSuggestedCategories() {
        const { suites, tags, tests } = this.runner;
        const parsedQuery = parseQuery(this.trimmedQuery());

        this.categories.suite.set(this.filterItems(parsedQuery, suites, "id"));
        this.categories.tag.set(this.filterItems(parsedQuery, tags, "tag"));
        this.categories.test.set(this.filterItems(parsedQuery, tests, "id"));
    }

    focusSearchInput() {
        this.searchInputRef()?.focus();
    }

    getCategoryCounts() {
        const { includeSpecs } = this.runner;
        const { suites, tests } = this.runner;
        const counts = [];
        for (const category of this.categoryKeys) {
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
        return $values(this.runner.includeSpecs).some((values) =>
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

    /**
     * @param {string} query
     */
    hasExactFilter(query) {
        R_QUERY_EXACT.lastIndex = 0;
        return R_QUERY_EXACT.test(query);
    }

    /**
     * @param {string} query
     */
    hasRegExpFilter(query) {
        return R_REGEX.test(query);
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
            this.searchInputRef(),
            ...this.rootRef().querySelectorAll("input[type=radio]:checked:enabled"),
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
        if (!this.trimmedQuery()) {
            return;
        }
        const latestSearches = this.getLatestSearches();
        latestSearches.unshift(this.trimmedQuery());
        storageSet(STORAGE.searches, [...new Set(latestSearches)].slice(0, 5));
    }

    /**
     * @param {InputEvent & { currentTarget: HTMLInputElement }} ev
     */
    onSearchInputInput(ev) {
        this.query.set(ev.currentTarget.value);

        this.ui.resultsPage.set(0);

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

        if (this.config.fun()) {
            this.verifySecretSequenceStep(ev);
        }
    }

    /**
     * @param {SearchFilter} type
     * @param {string} id
     * @param {number} [value]
     */
    setInclude(type, id, value) {
        this.config.filter.set("");
        this.runner.include(type, id, value);
    }

    /**
     * @param {string} query
     */
    setQuery(query) {
        this.query.set(query);

        this.updateFilterParam();
        this.updateSuggestions();
        this.focusSearchInput();
    }

    toggleDebug() {
        this.config.debugTest.set(!this.config.debugTest());
    }

    /**
     * @param {Event} ev
     */
    toggleExact(ev) {
        ev.preventDefault();

        const currentQuery = this.trimmedQuery();
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
        const currentValue = this.runner.includeSpecs[type][id];
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

        const currentQuery = this.trimmedQuery();
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
            const includeSpecs = this.runner.includeSpecs[type];
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
        this.config.filter.set(this.trimmedQuery());
    }

    updateSuggestions() {
        this.isEmpty.set(this.computeIsEmpty());
        this.updateSuggestedCategories();
        this.showDropdown.set(true);
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

            this.runner.stop();
            this.runner.reporting.passed += this.runner.reporting.failed;
            this.runner.reporting.passed += this.runner.reporting.todo;
            this.runner.reporting.failed = 0;
            this.runner.reporting.todo = 0;
            for (const suite of this.runner.suites.values()) {
                suite.reporting.passed += suite.reporting.failed;
                suite.reporting.passed += suite.reporting.todo;
                suite.reporting.failed = 0;
                suite.reporting.todo = 0;
            }
            for (const test of this.runner.tests.values()) {
                test.config.todo = false;
                test.status.set(Test.PASSED);
                for (const result of test.results()) {
                    result.pass = true;
                    result.currentErrors = [];
                    for (const assertion of result.getEvents("assertion")) {
                        assertion.pass = true;
                    }
                }
            }
            console.warn("Secret sequence activated: all tests pass!");
        }
    }

    /**
     * @param {string} query
     */
    wrappedQuery(query) {
        return this.hasRegExpFilter(query) ? query : stringify(query);
    }
}
