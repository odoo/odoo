import { useState } from "@odoo/owl";
import { Deferred } from "@web/core/utils/concurrency";

export function useSourceLoader({ sources, onSourcesLoaded }) {
    let nextSourceId = 0;
    let nextOptionId = 0;
    /**@type {Deferred} */
    let loadingPromise = null;
    const _sources = [];

    const state = useState({
        optionsRev: 0,
    });

    const makeSource = (source) => ({
        id: ++nextSourceId,
        options: [],
        isLoading: false,
        placeholder: source.placeholder,
        optionSlot: source.optionSlot,
    });

    const makeOption = (option) => ({
        cssClass: "",
        data: {},
        ...option,
        id: ++nextOptionId,
        unselectable: !option.onSelect,
    });

    const clear = () => {
        _sources.splice(0, _sources.length);
        state.optionsRev++;
    };

    const load = async (request) => {
        loadingPromise = loadingPromise || new Deferred();
        const currentPromise = loadingPromise;

        clear();

        const proms = [];
        for (const pSource of sources) {
            const source = makeSource(pSource);
            _sources.push(source);

            const options =
                typeof pSource.options === "function" ? pSource.options(request) : pSource.options;

            if (options instanceof Promise) {
                source.isLoading = true;
                const prom = options.then((options) => {
                    source.options = options.map((option) => makeOption(option));
                    source.isLoading = false;
                    state.optionsRev++;
                });
                proms.push(prom);
            } else {
                source.options = options.map((option) => makeOption(option));
            }
        }

        try {
            await Promise.all(proms);
            currentPromise.resolve();
        } catch {
            currentPromise.reject();
        } finally {
            if (currentPromise === loadingPromise) {
                loadingPromise = null;
            }
            onSourcesLoaded?.();
        }
    };

    return {
        get hasOptions() {
            return _sources.some((s) => s && s.options.length >= 1);
        },
        get sources() {
            return _sources;
        },
        get isLoading() {
            return !!loadingPromise;
        },
        set isLoading(value) {
            if (value) {
                loadingPromise = loadingPromise || new Deferred();
            }
        },
        load,
        waitUntilLoaded: async () => {
            if (loadingPromise) {
                await loadingPromise;
            }
            return true;
        },
        clear,
    };
}
