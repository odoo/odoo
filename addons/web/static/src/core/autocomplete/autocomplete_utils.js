import { useState } from "@odoo/owl";
import { Deferred } from "@web/core/utils/concurrency";
import { useDebounced } from "@web/core/utils/timing";

export function useSourceLoader({ sources, inputRef, timeout, onSourcesLoaded, onProcessInput }) {

    let nextSourceId = 0;
    let nextOptionId = 0;
    /**@type {Deferred} */
    let loadingPromise = null;
    const _sources = [];

    const state = useState({
        optionsRev: 0,
    });

    const makeSource = (source) => {
        return {
            id: ++nextSourceId,
            options: [],
            isLoading: false,
            placeholder: source.placeholder,
            optionTemplate: source.optionTemplate,
            optionSlot: source.optionSlot,
        };
    };

    const makeOption = (option) => {
        return Object.assign(Object.create(option), {
            id: ++nextOptionId,
        });
    };

    const clear = () => {
        _sources.splice(0, _sources.length);
        state.optionsRev++;
    };

    const load = async (useInput) => {
        loadingPromise = loadingPromise || new Deferred();
        const currentPromise = loadingPromise;
        // loadingPromise = null;

        clear();

        const proms = [];
        for (const pSource of sources) {
            const source = makeSource(pSource);
            _sources.push(source);

            const request = useInput ? inputRef.el.value.trim() : "";
            const options = typeof pSource.options === "function" ?
                pSource.options(request) :
                pSource.options;

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

    const debounceProcessInput = useDebounced(() => {
        load(true);
        onProcessInput?.();
    }, timeout);

    return {
        get hasOptions() {
            return _sources.some(s => s && s.options.length >= 1);
        },
        get sources() {
            return _sources;
        },
        get isLoading() {
            return !!loadingPromise;
        },
        load,
        clear,
        processInput: () => {
            // Set loadingPromise early so that isLoading is true
            loadingPromise = loadingPromise || new Deferred();
            debounceProcessInput();
        },
        waitUntilLoaded: async () => {
            if (loadingPromise) {
                await loadingPromise;
            }
            return true;
        },
    };
}
