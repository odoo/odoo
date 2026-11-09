import { useSequential } from "@mail/utils/common/hooks";

import {
    computed,
    onWillDestroy,
    Plugin,
    signal,
    t,
    useConfig,
    useOnChange,
    useScope,
} from "@odoo/owl";

import { batched } from "@web/core/utils/timing";

/**
 * Shared search state machine for components that combine an optional async
 * fetch (typically an RPC) with an optional sync local lookup. Exposes reactive
 * fields (`searchTerm`, `searching`, `loading`, `results`) and methods (`run`,
 * `reset`). Subclass to add domain-specific fields while sharing the base logic.
 *
 * Pass `deps`, `fetch`, `filter`, `initialResults`, `isActive`, and `searchTerm`
 * directly in the configuration given to `providePlugins`. All are optional;
 * see the corresponding fields below for their contracts and defaults.
 *
 * Narrow-dedup: if `fetch` resolves to `false` for some term, the next term
 * that starts with it skips the fetch (a narrower query cannot have results
 * when the broader one had none). Resolve to anything else to disable this for
 * the current bookmark. It is dropped when the deps change and on `reset()`.
 */
export class SearchStatePlugin extends Plugin {
    _loading = signal(false);
    /** @type {import("@odoo/owl").Signal<any>} */
    _results = signal();
    _searching = signal(false);
    /**
     * Backing store of {@link searchTerm}, a local signal unless the parent
     * passed one through the `searchTerm` configuration. Reads and writes use
     * that signal directly; reset never clears a parent-owned signal.
     *
     * @type {import("@odoo/owl").Signal<string>}
     */
    _searchTerm = signal("");
    /**
     * Extra reactive values that re-run the search when they change.
     * Defaults to no dependencies.
     *
     * @type {(() => any[]) | undefined}
     */
    depsGetter = useConfig("deps", t.function([], t.array()).optional());
    deps = computed(() => this.depsGetter?.() ?? []);
    /**
     * Optional async fetch, given a signal aborted when a new fetch supersedes it.
     * Resolve to `false` to skip subsequent fetches for narrower terms.
     *
     * @type {((term: string, options: { abortSignal: AbortSignal }) => Promise<boolean | void>) | undefined}
     */
    fetch = useConfig(
        "fetch",
        t
            .function(
                [t.string(), t.object({ abortSignal: t.instanceOf(AbortSignal) })],
                t.promise(t.boolean().optional())
            )
            .optional()
    );
    /**
     * Optional synchronous lookup producing `results`. Runs on term/dependency
     * changes (once per animation frame) and again after the fetch completes.
     *
     * @type {((term: string) => any) | undefined}
     */
    filter = useConfig("filter", t.function([t.string()], t.any()).optional());
    /** Value assigned to `results` on reset. Defaults to a fresh empty array. */
    initialResults = useConfig(
        "initialResults",
        t.any().optional(() => [])
    );
    /**
     * Optional predicate overriding the default non-empty-term check, e.g. to
     * keep mention suggestions active for an empty term after a delimiter.
     *
     * @type {(() => boolean) | undefined}
     */
    isActiveGetter = useConfig("isActive", t.function([], t.boolean()).optional());
    isActive = computed(() => (this.isActiveGetter ? this.isActiveGetter() : !!this.searchTerm));
    /** @type {string | undefined} */
    lastEmptyTerm;
    /** Whether {@link _searchTerm} is ours to clear, i.e. not the parent's. */
    ownsSearchTerm = true;
    /** @type {Function | undefined} */
    sequential;

    setup() {
        const searchTerm = useConfig("searchTerm", t.signal(t.string()).optional());
        if (searchTerm) {
            this._searchTerm = searchTerm;
            this.ownsSearchTerm = false;
        }
        this.results = this.initialResults;
        this.sequential = useSequential();
        const scope = useScope();
        // once per animation frame, like the rendering: searching on each change
        // (e.g. each typed character) would fetch every intermediate term
        const update = batched(
            () => {
                if (scope.isDestroyed()) {
                    return;
                }
                if (!this.isActive()) {
                    this.reset();
                    return;
                }
                if (this.filter) {
                    this.results = this.filter(this.searchTerm);
                }
                this.run();
            },
            () => new Promise((resolve) => requestAnimationFrame(resolve))
        );
        useOnChange(
            () => this.deps(),
            () => {
                this.lastEmptyTerm = undefined;
            }
        );
        useOnChange(
            () => [this.searchTerm, ...this.deps()],
            () => {
                update();
            }
        );
        onWillDestroy(() => this.reset());
    }

    get loading() {
        return this._loading();
    }

    set loading(value) {
        this._loading.set(value);
    }

    get results() {
        return this._results();
    }

    set results(value) {
        this._results.set(value);
    }

    get searching() {
        return this._searching();
    }

    set searching(value) {
        this._searching.set(value);
    }

    get searchTerm() {
        return this._searchTerm();
    }

    set searchTerm(value) {
        this._searchTerm.set(value);
    }

    reset() {
        if (this.ownsSearchTerm) {
            this.searchTerm = "";
        }
        this.searching = false;
        this.loading = false;
        this.results = this.initialResults;
        this.lastEmptyTerm = undefined;
    }

    async run({ skipFetch = false } = {}) {
        if (!this.isActive()) {
            this.reset();
            return;
        }
        const term = this.searchTerm;
        this.searching = true;
        if (this.lastEmptyTerm !== undefined && term.startsWith(this.lastEmptyTerm)) {
            // Broader term already had no results, so the narrower term
            // can't either — skip both the fetch and the local filter.
            return;
        }
        if (this.fetch && !skipFetch) {
            await this.sequential(async (abortSignal) => {
                if (!this.isActive()) {
                    return;
                }
                this.loading = true;
                let result;
                try {
                    result = await this.fetch(term, { abortSignal });
                } catch (e) {
                    if (!abortSignal.aborted) {
                        throw e;
                    }
                } finally {
                    if (this.searchTerm === term) {
                        this.loading = false;
                    }
                }
                if (this.searchTerm === term) {
                    if (this.filter) {
                        this.results = this.filter(term);
                    }
                    this.lastEmptyTerm = result === false ? term : undefined;
                }
            });
        } else if (this.filter) {
            this.results = this.filter(term);
        }
    }
}
