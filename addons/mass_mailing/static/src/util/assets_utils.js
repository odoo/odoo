import { assets, AssetsLoadingError, getBundle } from "@web/core/assets";

const CSSSheetsCache = new Map();

/**
 * Get common stylesheets used for every mail template
 *
 * @returns {Promise<Array<CSSStyleSheet>>}
 */
export async function getStyleSheets(scope, iframe, assetName) {
    const { cssLibs } = await getBundle(assetName);
    const loadCSSPromises = [];
    if (cssLibs) {
        loadCSSPromises.push(...cssLibs.map((url) => loadCSSSheets(url)));
    }
    const cssTexts = await Promise.all(loadCSSPromises);
    if (scope.isDestroyed()) {
        return [];
    }
    const sheetPromises = [];
    for (const cssText of cssTexts) {
        const win = iframe.contentDocument.defaultView;
        const sheet = new win.CSSStyleSheet();
        sheetPromises.push(sheet.replace(cssText).then(() => sheet));
    }
    return Promise.all(sheetPromises);
}

/**
 * Custom load which does not add the CSSStyleSheet in the current document
 */
function loadCSSSheets(url, retryCount = 0) {
    if (CSSSheetsCache.has(url)) {
        return CSSSheetsCache.get(url);
    }
    const promise = new Promise((resolve, reject) =>
        fetch(url)
            .then((response) => {
                if (!response.ok) {
                    reject(
                        new AssetsLoadingError(`The loading of ${url} failed`, {
                            cause: response.status,
                        })
                    );
                }
                return response.text();
            })
            .then(resolve)
            .catch(async (error) => {
                CSSSheetsCache.delete(url);
                if (retryCount < assets.retries.count) {
                    const delay = assets.retries.delay + assets.retries.extraDelay * retryCount;
                    await new Promise((res) => setTimeout(res, delay));
                    loadCSSSheets(url, retryCount + 1)
                        .then(resolve)
                        .catch((reason) => {
                            CSSSheetsCache.delete(url);
                            reject(reason);
                        });
                } else {
                    reject(
                        new AssetsLoadingError(`The loading of ${url} failed`, { cause: error })
                    );
                }
            })
    );
    CSSSheetsCache.set(url, promise);
    return promise;
}
