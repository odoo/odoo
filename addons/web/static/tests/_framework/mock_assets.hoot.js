// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

const { loader } = odoo;

/**
 * @param {string} moduleName
 * @param {Record<string, unknown>} mockModules
 */
function startWithMockModules(moduleName, mockModules) {
    const addedModules = new Set();
    const originalModules = new Map();
    const mockModuleEntries = Object.entries(mockModules);
    for (const [name, mockModule] of mockModuleEntries) {
        if (loader.modules.has(name)) {
            originalModules.set(name, loader.modules.get(name));
        } else {
            addedModules.add(name);
        }
        loader.modules.set(name, mockModule);
    }

    const result = loader.startModule(moduleName);

    for (const [name, originalModule] of originalModules) {
        loader.modules.set(name, originalModule);
    }
    for (const name of addedModules) {
        loader.modules.delete(name);
    }

    return result;
}

/**
 * @param {Promise<unknown>} promise
 * @param {() => void} forget
 */
function forgetIfPendingAfterTest(promise, forget) {
    let isPending = true;
    const onSettled = () => (isPending = false);
    promise.then(onSettled, onSettled);
    // Forget a promise pending at the end of its test: Hoot never settles its fetch.
    after(() => {
        if (isPending) {
            forget();
        }
    });
}

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Browser module needs to be mocked to patch the `location` global object since
 * it can't be directly mocked on the window object.
 *
 * @param {string} name
 */
export function mockAssetsFactory(name) {
    return function mockAssets() {
        if (loader.modules.has(name)) {
            return loader.modules.get(name);
        }
<<<<<<< 314100a8860e1361d67ad0af36f4175daac50a4e
        return startWithMockModules(name, { "@web/session": { session: {} } });
||||||| 3eeaca8ece38fe2ad86b7bdd7aea133019412676
        const assetsModule = startWithMockModules(name, { "@web/session": { session: {} } });
        const { assets } = assetsModule;
        const { getBundle } = assets;
        assets.getBundle = function mockGetBundle(bundleName) {
            const { globalCache } = assets;
            const isCached = globalCache.has(bundleName);
            const promise = getBundle(bundleName);
            if (!isCached) {
                let isPending = true;
                const onSettled = () => (isPending = false);
                promise.then(onSettled, onSettled);
                // Remove a bundle pending at the end of its test: Hoot never settles its fetch.
                after(() => {
                    if (isPending && globalCache.get(bundleName) === promise) {
                        globalCache.delete(bundleName);
                    }
                });
            }
            return promise;
        };
        return assetsModule;
=======
        const assetsModule = startWithMockModules(name, { "@web/session": { session: {} } });
        const { assets } = assetsModule;
        const { getBundle } = assets;
        assets.getBundle = function mockGetBundle(bundleName) {
            const { globalCache } = assets;
            const isCached = globalCache.has(bundleName);
            const promise = getBundle(bundleName);
            if (!isCached) {
                forgetIfPendingAfterTest(promise, () => {
                    if (globalCache.get(bundleName) === promise) {
                        globalCache.delete(bundleName);
                    }
                });
            }
            return promise;
        };
        return assetsModule;
>>>>>>> 9df0335ae510df80ab0a5fcc6b5ea79d2472aa3c
    };
}

/**
 * @param {string} name
 */
export function mockEmojiLoaderFactory(name) {
    return function mockEmojiLoader() {
        if (loader.modules.has(name)) {
            return loader.modules.get(name);
        }
        const emojiLoaderModule = loader.startModule(name);
        const { emojiLoader } = emojiLoaderModule;
        const { load } = emojiLoader;
        emojiLoader.load = function mockLoad() {
            const isLoading = Boolean(emojiLoader._loadingPromise);
            const promise = load.call(emojiLoader, ...arguments);
            if (!isLoading) {
                forgetIfPendingAfterTest(promise, () => {
                    if (emojiLoader._loadingPromise === promise) {
                        emojiLoader._loadingPromise = null;
                    }
                });
            }
            return promise;
        };
        return emojiLoaderModule;
    };
}
