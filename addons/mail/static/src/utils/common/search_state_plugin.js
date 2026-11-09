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
 * Shared search state with optional async fetch and sync local lookup.
 *
 * Config (all optional):
 * - `deps`: function returning extra reactive dependencies that re-run the search.
 * - `fetch`: async function fetching results for the term, with an abort signal.
 * - `filter`: function returning local results for the term.
 * - `initialResults`: function returning the results used on reset, defaults to an empty array.
 * - `isActive`: predicate overriding the default non-empty-term check.
 * - `searchTerm`: parent-owned signal for the term, defaults to a local signal.
 */
export class SearchStatePlugin extends Plugin {
    /** @type {(() => any[]) | undefined} Extra dependencies that re-run the search when changed. */
    depsGetter = useConfig("deps", t.function([], t.array()).optional());
    deps = computed(() => this.depsGetter?.() ?? []);
    /**
     * @type {((term: string, options: { abortSignal: AbortSignal }) => Promise<boolean | void>) | undefined}
     * Next fetch aborts the signal; `false` skips narrower terms until deps change or reset.
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
     * @type {((term: string) => any) | undefined}
     * Local lookup on term/deps changes (once per animation frame) and after fetch.
     */
    filter = useConfig("filter", t.function([t.string()], t.any()).optional());
    /** @type {(() => any) | undefined} Returns the value assigned to `results` on reset. */
    initialResultsGetter = useConfig("initialResults", t.function([], t.any()).optional());
    initialResults = computed(() => this.initialResultsGetter?.() ?? []);
    /** @type {(() => boolean) | undefined} Overrides the default non-empty-term check. */
    isActiveGetter = useConfig("isActive", t.function([], t.boolean()).optional());
    isActive = computed(() => (this.isActiveGetter ? this.isActiveGetter() : !!this.searchTerm()));
    /** @type {string | undefined} */
    lastEmptyTerm;
    loading = signal(false);
    /** Whether {@link searchTerm} is ours to clear, i.e. not the parent's. */
    ownsSearchTerm = true;
    /** @type {import("@odoo/owl").Signal<any>} */
    results = signal();
    searching = signal(false);
    /** @type {import("@odoo/owl").Signal<string>} from the `searchTerm` config, else local */
    searchTerm = signal("");
    /** @type {Function | undefined} */
    sequential;

    setup() {
        const searchTerm = useConfig("searchTerm", t.signal(t.string()).optional());
        if (searchTerm) {
            this.searchTerm = searchTerm;
            this.ownsSearchTerm = false;
        }
        this.results.set(this.initialResults());
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
                    this.results.set(this.filter(this.searchTerm()));
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
            () => [this.searchTerm(), ...this.deps()],
            () => {
                update();
            }
        );
        onWillDestroy(() => this.reset());
    }

    reset() {
        if (this.ownsSearchTerm) {
            this.searchTerm.set("");
        }
        this.searching.set(false);
        this.loading.set(false);
        this.results.set(this.initialResults());
        this.lastEmptyTerm = undefined;
    }

    async run({ skipFetch = false } = {}) {
        if (!this.isActive()) {
            this.reset();
            return;
        }
        const term = this.searchTerm();
        this.searching.set(true);
        if (this.lastEmptyTerm !== undefined && term.startsWith(this.lastEmptyTerm)) {
            // Broader term already had no results, so the narrower term
            // can't either: skip both the fetch and the local filter.
            // A fetch still running for a previous term does not clear `loading`.
            this.loading.set(false);
            return;
        }
        if (this.fetch && !skipFetch) {
            await this.sequential(async (abortSignal) => {
                if (!this.isActive()) {
                    return;
                }
                this.loading.set(true);
                let result;
                try {
                    result = await this.fetch(term, { abortSignal });
                } catch (e) {
                    if (!abortSignal.aborted) {
                        throw e;
                    }
                } finally {
                    if (this.searchTerm() === term) {
                        this.loading.set(false);
                    }
                }
                if (this.searchTerm() === term) {
                    if (this.filter) {
                        this.results.set(this.filter(term));
                    }
                    this.lastEmptyTerm = result === false ? term : undefined;
                }
            });
        } else if (this.filter) {
            this.results.set(this.filter(term));
        }
    }
}
