// This script is to be called directly in the <head>. It should not import any
// other file or library, as it cannot be transformed into a module (because a
// module is deferred): the function should be the very first thing launched on
// the page to be able to bypass other IIFE of 3rd-party services that inject
// new scripts client-side.

// eslint-disable-next-line no-unused-vars
function watch3rdPartyScripts(thirdPartyDomainsBlockList) {
    const removeWWW = (domain) => (domain.startsWith("www.") ? domain.slice(4) : domain);
    const blockList = thirdPartyDomainsBlockList.map(removeWWW);
    const cookieRegex = /(^|(; ))website_cookies_bar=(?<value>[^;]+)/;
    const scriptSrcDesc = Object.getOwnPropertyDescriptor(HTMLScriptElement.prototype, "src");
    Object.defineProperty(HTMLScriptElement.prototype, "_src", scriptSrcDesc);
    Object.defineProperty(HTMLScriptElement.prototype, "src", {
        enumerable: true,
        configurable: true,
        get() {
            return this._src;
        },
        set(val) {
            const cookiesBarCookie = document.cookie.match(cookieRegex)?.groups.value;
            const host = removeWWW(new URL(val, window.location.origin).host.toLowerCase());
            if (
                (!cookiesBarCookie || !JSON.parse(cookiesBarCookie).optional) &&
                blockList.some((domain) => host === domain || host.endsWith(`.${domain}`))
            ) {
                this.dataset.nocookieSrc = val;
                this.dataset.needCookiesApproval = "true";
                this._src = "about:blank";
            } else {
                this._src = val;
            }
        },
    });
    document.addEventListener(
        "optionalCookiesAccepted",
        () => {
            for (const scriptEl of document.querySelectorAll(
                "script[data-need-cookies-approval]"
            )) {
                // We have to completely recreate the scripts for them to fire, we
                // cannot just switch the src.
                const newScript = document.createElement("script");
                newScript._src = scriptEl.dataset.nocookieSrc;
                scriptEl.insertAdjacentElement("beforebegin", newScript);
                scriptEl.remove();
            }
        },
        { once: true }
    );
}
