/*!
FullCalendar Core v6.1.20
Docs & License: https://fullcalendar.io
(c) 2024 Adam Shaw
*/
var FullCalendar = (function (exports) {
    'use strict';

    const styleTexts = [];
    const styleEls = new Map();
    function injectStyles(styleText) {
        styleTexts.push(styleText);
        styleEls.forEach((styleEl) => {
            appendStylesTo(styleEl, styleText);
        });
    }
    function ensureElHasStyles(el) {
        if (el.isConnected && // sometimes true if SSR system simulates DOM
            el.getRootNode // sometimes undefined if SSR system simulates DOM
        ) {
            registerStylesRoot(el.getRootNode());
        }
    }
    function registerStylesRoot(rootNode) {
        let styleEl = styleEls.get(rootNode);
        if (!styleEl || !styleEl.isConnected) {
            styleEl = rootNode.querySelector('style[data-fullcalendar]');
            if (!styleEl) {
                styleEl = document.createElement('style');
                styleEl.setAttribute('data-fullcalendar', '');
                const nonce = getNonceValue();
                if (nonce) {
                    styleEl.nonce = nonce;
                }
                const parentEl = rootNode === document ? document.head : rootNode;
                const insertBefore = rootNode === document
                    ? parentEl.querySelector('script,link[rel=stylesheet],link[as=style],style')
                    : parentEl.firstChild;
                parentEl.insertBefore(styleEl, insertBefore);
            }
            styleEls.set(rootNode, styleEl);
            hydrateStylesRoot(styleEl);
        }
    }
    function hydrateStylesRoot(styleEl) {
        for (const styleText of styleTexts) {
            appendStylesTo(styleEl, styleText);
        }
    }
    function appendStylesTo(styleEl, styleText) {
        const { sheet } = styleEl;
        const ruleCnt = sheet.cssRules.length;
        styleText.split('}').forEach((styleStr, i) => {
            styleStr = styleStr.trim();
            if (styleStr) {
                sheet.insertRule(styleStr + '}', ruleCnt + i);
            }
        });
    }
    // nonce
    // -------------------------------------------------------------------------------------------------
    let queriedNonceValue;
    function getNonceValue() {
        if (queriedNonceValue === undefined) {
            queriedNonceValue = queryNonceValue();
        }
        return queriedNonceValue;
    }
    /*
    TODO: discourage meta tag and instead put nonce attribute on placeholder <style> tag
    */
    function queryNonceValue() {
        const metaWithNonce = document.querySelector('meta[name="csp-nonce"]');
        if (metaWithNonce && metaWithNonce.hasAttribute('content')) {
            return metaWithNonce.getAttribute('content');
        }
        const elWithNonce = document.querySelector('script[nonce]');
        if (elWithNonce) {
            return elWithNonce.nonce || '';
        }
        return '';
    }
    // main
    // -------------------------------------------------------------------------------------------------
    if (typeof document !== 'undefined') {
        registerStylesRoot(document);
    }

    var css_248z = ":root{--fc-small-font-size:.85em;--fc-page-bg-color:#fff;--fc-neutral-bg-color:hsla(0,0%,82%,.3);--fc-neutral-text-color:grey;--fc-border-color:#ddd;--fc-button-text-color:#fff;--fc-button-bg-color:#2c3e50;--fc-button-border-color:#2c3e50;--fc-button-hover-bg-color:#1e2b37;--fc-button-hover-border-color:#1a252f;--fc-button-active-bg-color:#1a252f;--fc-button-active-border-color:#151e27;--fc-event-bg-color:#3788d8;--fc-event-border-color:#3788d8;--fc-event-text-color:#fff;--fc-event-selected-overlay-color:rgba(0,0,0,.25);--fc-more-link-bg-color:#d0d0d0;--fc-more-link-text-color:inherit;--fc-event-resizer-thickness:8px;--fc-event-resizer-dot-total-width:8px;--fc-event-resizer-dot-border-width:1px;--fc-non-business-color:hsla(0,0%,84%,.3);--fc-bg-event-color:#8fdf82;--fc-bg-event-opacity:0.3;--fc-highlight-color:rgba(188,232,241,.3);--fc-today-bg-color:rgba(255,220,40,.15);--fc-now-indicator-color:red}.fc-not-allowed,.fc-not-allowed .fc-event{cursor:not-allowed}.fc{display:flex;flex-direction:column;font-size:1em}.fc,.fc *,.fc :after,.fc :before{box-sizing:border-box}.fc table{border-collapse:collapse;border-spacing:0;font-size:1em}.fc th{text-align:center}.fc td,.fc th{padding:0;vertical-align:top}.fc a[data-navlink]{cursor:pointer}.fc a[data-navlink]:hover{text-decoration:underline}.fc-direction-ltr{direction:ltr;text-align:left}.fc-direction-rtl{direction:rtl;text-align:right}.fc-theme-standard td,.fc-theme-standard th{border:1px solid var(--fc-border-color)}.fc-liquid-hack td,.fc-liquid-hack th{position:relative}@font-face{font-family:fcicons;font-style:normal;font-weight:400;src:url(\"data:application/x-font-ttf;charset=utf-8;base64,AAEAAAALAIAAAwAwT1MvMg8SBfAAAAC8AAAAYGNtYXAXVtKNAAABHAAAAFRnYXNwAAAAEAAAAXAAAAAIZ2x5ZgYydxIAAAF4AAAFNGhlYWQUJ7cIAAAGrAAAADZoaGVhB20DzAAABuQAAAAkaG10eCIABhQAAAcIAAAALGxvY2ED4AU6AAAHNAAAABhtYXhwAA8AjAAAB0wAAAAgbmFtZXsr690AAAdsAAABhnBvc3QAAwAAAAAI9AAAACAAAwPAAZAABQAAApkCzAAAAI8CmQLMAAAB6wAzAQkAAAAAAAAAAAAAAAAAAAABEAAAAAAAAAAAAAAAAAAAAABAAADpBgPA/8AAQAPAAEAAAAABAAAAAAAAAAAAAAAgAAAAAAADAAAAAwAAABwAAQADAAAAHAADAAEAAAAcAAQAOAAAAAoACAACAAIAAQAg6Qb//f//AAAAAAAg6QD//f//AAH/4xcEAAMAAQAAAAAAAAAAAAAAAQAB//8ADwABAAAAAAAAAAAAAgAANzkBAAAAAAEAAAAAAAAAAAACAAA3OQEAAAAAAQAAAAAAAAAAAAIAADc5AQAAAAABAWIAjQKeAskAEwAAJSc3NjQnJiIHAQYUFwEWMjc2NCcCnuLiDQ0MJAz/AA0NAQAMJAwNDcni4gwjDQwM/wANIwz/AA0NDCMNAAAAAQFiAI0CngLJABMAACUBNjQnASYiBwYUHwEHBhQXFjI3AZ4BAA0N/wAMJAwNDeLiDQ0MJAyNAQAMIw0BAAwMDSMM4uINIwwNDQAAAAIA4gC3Ax4CngATACcAACUnNzY0JyYiDwEGFB8BFjI3NjQnISc3NjQnJiIPAQYUHwEWMjc2NCcB87e3DQ0MIw3VDQ3VDSMMDQ0BK7e3DQ0MJAzVDQ3VDCQMDQ3zuLcMJAwNDdUNIwzWDAwNIwy4twwkDA0N1Q0jDNYMDA0jDAAAAgDiALcDHgKeABMAJwAAJTc2NC8BJiIHBhQfAQcGFBcWMjchNzY0LwEmIgcGFB8BBwYUFxYyNwJJ1Q0N1Q0jDA0Nt7cNDQwjDf7V1Q0N1QwkDA0Nt7cNDQwkDLfWDCMN1Q0NDCQMt7gMIw0MDNYMIw3VDQ0MJAy3uAwjDQwMAAADAFUAAAOrA1UAMwBoAHcAABMiBgcOAQcOAQcOARURFBYXHgEXHgEXHgEzITI2Nz4BNz4BNz4BNRE0JicuAScuAScuASMFITIWFx4BFx4BFx4BFREUBgcOAQcOAQcOASMhIiYnLgEnLgEnLgE1ETQ2Nz4BNz4BNz4BMxMhMjY1NCYjISIGFRQWM9UNGAwLFQkJDgUFBQUFBQ4JCRULDBgNAlYNGAwLFQkJDgUFBQUFBQ4JCRULDBgN/aoCVgQIBAQHAwMFAQIBAQIBBQMDBwQECAT9qgQIBAQHAwMFAQIBAQIBBQMDBwQECASAAVYRGRkR/qoRGRkRA1UFBAUOCQkVDAsZDf2rDRkLDBUJCA4FBQUFBQUOCQgVDAsZDQJVDRkLDBUJCQ4FBAVVAgECBQMCBwQECAX9qwQJAwQHAwMFAQICAgIBBQMDBwQDCQQCVQUIBAQHAgMFAgEC/oAZEhEZGRESGQAAAAADAFUAAAOrA1UAMwBoAIkAABMiBgcOAQcOAQcOARURFBYXHgEXHgEXHgEzITI2Nz4BNz4BNz4BNRE0JicuAScuAScuASMFITIWFx4BFx4BFx4BFREUBgcOAQcOAQcOASMhIiYnLgEnLgEnLgE1ETQ2Nz4BNz4BNz4BMxMzFRQWMzI2PQEzMjY1NCYrATU0JiMiBh0BIyIGFRQWM9UNGAwLFQkJDgUFBQUFBQ4JCRULDBgNAlYNGAwLFQkJDgUFBQUFBQ4JCRULDBgN/aoCVgQIBAQHAwMFAQIBAQIBBQMDBwQECAT9qgQIBAQHAwMFAQIBAQIBBQMDBwQECASAgBkSEhmAERkZEYAZEhIZgBEZGREDVQUEBQ4JCRUMCxkN/asNGQsMFQkIDgUFBQUFBQ4JCBUMCxkNAlUNGQsMFQkJDgUEBVUCAQIFAwIHBAQIBf2rBAkDBAcDAwUBAgICAgEFAwMHBAMJBAJVBQgEBAcCAwUCAQL+gIASGRkSgBkSERmAEhkZEoAZERIZAAABAOIAjQMeAskAIAAAExcHBhQXFjI/ARcWMjc2NC8BNzY0JyYiDwEnJiIHBhQX4uLiDQ0MJAzi4gwkDA0N4uINDQwkDOLiDCQMDQ0CjeLiDSMMDQ3h4Q0NDCMN4uIMIw0MDOLiDAwNIwwAAAABAAAAAQAAa5n0y18PPPUACwQAAAAAANivOVsAAAAA2K85WwAAAAADqwNVAAAACAACAAAAAAAAAAEAAAPA/8AAAAQAAAAAAAOrAAEAAAAAAAAAAAAAAAAAAAALBAAAAAAAAAAAAAAAAgAAAAQAAWIEAAFiBAAA4gQAAOIEAABVBAAAVQQAAOIAAAAAAAoAFAAeAEQAagCqAOoBngJkApoAAQAAAAsAigADAAAAAAACAAAAAAAAAAAAAAAAAAAAAAAAAA4ArgABAAAAAAABAAcAAAABAAAAAAACAAcAYAABAAAAAAADAAcANgABAAAAAAAEAAcAdQABAAAAAAAFAAsAFQABAAAAAAAGAAcASwABAAAAAAAKABoAigADAAEECQABAA4ABwADAAEECQACAA4AZwADAAEECQADAA4APQADAAEECQAEAA4AfAADAAEECQAFABYAIAADAAEECQAGAA4AUgADAAEECQAKADQApGZjaWNvbnMAZgBjAGkAYwBvAG4Ac1ZlcnNpb24gMS4wAFYAZQByAHMAaQBvAG4AIAAxAC4AMGZjaWNvbnMAZgBjAGkAYwBvAG4Ac2ZjaWNvbnMAZgBjAGkAYwBvAG4Ac1JlZ3VsYXIAUgBlAGcAdQBsAGEAcmZjaWNvbnMAZgBjAGkAYwBvAG4Ac0ZvbnQgZ2VuZXJhdGVkIGJ5IEljb01vb24uAEYAbwBuAHQAIABnAGUAbgBlAHIAYQB0AGUAZAAgAGIAeQAgAEkAYwBvAE0AbwBvAG4ALgAAAAMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\") format(\"truetype\")}.fc-icon{speak:none;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;display:inline-block;font-family:fcicons!important;font-style:normal;font-variant:normal;font-weight:400;height:1em;line-height:1;text-align:center;text-transform:none;-webkit-user-select:none;-moz-user-select:none;user-select:none;width:1em}.fc-icon-chevron-left:before{content:\"\\e900\"}.fc-icon-chevron-right:before{content:\"\\e901\"}.fc-icon-chevrons-left:before{content:\"\\e902\"}.fc-icon-chevrons-right:before{content:\"\\e903\"}.fc-icon-minus-square:before{content:\"\\e904\"}.fc-icon-plus-square:before{content:\"\\e905\"}.fc-icon-x:before{content:\"\\e906\"}.fc .fc-button{border-radius:0;font-family:inherit;font-size:inherit;line-height:inherit;margin:0;overflow:visible;text-transform:none}.fc .fc-button:focus{outline:1px dotted;outline:5px auto -webkit-focus-ring-color}.fc .fc-button{-webkit-appearance:button}.fc .fc-button:not(:disabled){cursor:pointer}.fc .fc-button{background-color:transparent;border:1px solid transparent;border-radius:.25em;display:inline-block;font-size:1em;font-weight:400;line-height:1.5;padding:.4em .65em;text-align:center;-webkit-user-select:none;-moz-user-select:none;user-select:none;vertical-align:middle}.fc .fc-button:hover{text-decoration:none}.fc .fc-button:focus{box-shadow:0 0 0 .2rem rgba(44,62,80,.25);outline:0}.fc .fc-button:disabled{opacity:.65}.fc .fc-button-primary{background-color:var(--fc-button-bg-color);border-color:var(--fc-button-border-color);color:var(--fc-button-text-color)}.fc .fc-button-primary:hover{background-color:var(--fc-button-hover-bg-color);border-color:var(--fc-button-hover-border-color);color:var(--fc-button-text-color)}.fc .fc-button-primary:disabled{background-color:var(--fc-button-bg-color);border-color:var(--fc-button-border-color);color:var(--fc-button-text-color)}.fc .fc-button-primary:focus{box-shadow:0 0 0 .2rem rgba(76,91,106,.5)}.fc .fc-button-primary:not(:disabled).fc-button-active,.fc .fc-button-primary:not(:disabled):active{background-color:var(--fc-button-active-bg-color);border-color:var(--fc-button-active-border-color);color:var(--fc-button-text-color)}.fc .fc-button-primary:not(:disabled).fc-button-active:focus,.fc .fc-button-primary:not(:disabled):active:focus{box-shadow:0 0 0 .2rem rgba(76,91,106,.5)}.fc .fc-button .fc-icon{font-size:1.5em;vertical-align:middle}.fc .fc-button-group{display:inline-flex;position:relative;vertical-align:middle}.fc .fc-button-group>.fc-button{flex:1 1 auto;position:relative}.fc .fc-button-group>.fc-button.fc-button-active,.fc .fc-button-group>.fc-button:active,.fc .fc-button-group>.fc-button:focus,.fc .fc-button-group>.fc-button:hover{z-index:1}.fc-direction-ltr .fc-button-group>.fc-button:not(:first-child){border-bottom-left-radius:0;border-top-left-radius:0;margin-left:-1px}.fc-direction-ltr .fc-button-group>.fc-button:not(:last-child){border-bottom-right-radius:0;border-top-right-radius:0}.fc-direction-rtl .fc-button-group>.fc-button:not(:first-child){border-bottom-right-radius:0;border-top-right-radius:0;margin-right:-1px}.fc-direction-rtl .fc-button-group>.fc-button:not(:last-child){border-bottom-left-radius:0;border-top-left-radius:0}.fc .fc-toolbar{align-items:center;display:flex;justify-content:space-between}.fc .fc-toolbar.fc-header-toolbar{margin-bottom:1.5em}.fc .fc-toolbar.fc-footer-toolbar{margin-top:1.5em}.fc .fc-toolbar-title{font-size:1.75em;margin:0}.fc-direction-ltr .fc-toolbar>*>:not(:first-child){margin-left:.75em}.fc-direction-rtl .fc-toolbar>*>:not(:first-child){margin-right:.75em}.fc-direction-rtl .fc-toolbar-ltr{flex-direction:row-reverse}.fc .fc-scroller{-webkit-overflow-scrolling:touch;position:relative}.fc .fc-scroller-liquid{height:100%}.fc .fc-scroller-liquid-absolute{bottom:0;left:0;position:absolute;right:0;top:0}.fc .fc-scroller-harness{direction:ltr;overflow:hidden;position:relative}.fc .fc-scroller-harness-liquid{height:100%}.fc-direction-rtl .fc-scroller-harness>.fc-scroller{direction:rtl}.fc-theme-standard .fc-scrollgrid{border:1px solid var(--fc-border-color)}.fc .fc-scrollgrid,.fc .fc-scrollgrid table{table-layout:fixed;width:100%}.fc .fc-scrollgrid table{border-left-style:hidden;border-right-style:hidden;border-top-style:hidden}.fc .fc-scrollgrid{border-bottom-width:0;border-collapse:separate;border-right-width:0}.fc .fc-scrollgrid-liquid{height:100%}.fc .fc-scrollgrid-section,.fc .fc-scrollgrid-section table,.fc .fc-scrollgrid-section>td{height:1px}.fc .fc-scrollgrid-section-liquid>td{height:100%}.fc .fc-scrollgrid-section>*{border-left-width:0;border-top-width:0}.fc .fc-scrollgrid-section-footer>*,.fc .fc-scrollgrid-section-header>*{border-bottom-width:0}.fc .fc-scrollgrid-section-body table,.fc .fc-scrollgrid-section-footer table{border-bottom-style:hidden}.fc .fc-scrollgrid-section-sticky>*{background:var(--fc-page-bg-color);position:sticky;z-index:3}.fc .fc-scrollgrid-section-header.fc-scrollgrid-section-sticky>*{top:0}.fc .fc-scrollgrid-section-footer.fc-scrollgrid-section-sticky>*{bottom:0}.fc .fc-scrollgrid-sticky-shim{height:1px;margin-bottom:-1px}.fc-sticky{position:sticky}.fc .fc-view-harness{flex-grow:1;position:relative}.fc .fc-view-harness-active>.fc-view{bottom:0;left:0;position:absolute;right:0;top:0}.fc .fc-col-header-cell-cushion{display:inline-block;padding:2px 4px}.fc .fc-bg-event,.fc .fc-highlight,.fc .fc-non-business{bottom:0;left:0;position:absolute;right:0;top:0}.fc .fc-non-business{background:var(--fc-non-business-color)}.fc .fc-bg-event{background:var(--fc-bg-event-color);opacity:var(--fc-bg-event-opacity)}.fc .fc-bg-event .fc-event-title{font-size:var(--fc-small-font-size);font-style:italic;margin:.5em}.fc .fc-highlight{background:var(--fc-highlight-color)}.fc .fc-cell-shaded,.fc .fc-day-disabled{background:var(--fc-neutral-bg-color)}a.fc-event,a.fc-event:hover{text-decoration:none}.fc-event.fc-event-draggable,.fc-event[href]{cursor:pointer}.fc-event .fc-event-main{position:relative;z-index:2}.fc-event-dragging:not(.fc-event-selected){opacity:.75}.fc-event-dragging.fc-event-selected{box-shadow:0 2px 7px rgba(0,0,0,.3)}.fc-event .fc-event-resizer{display:none;position:absolute;z-index:4}.fc-event-selected .fc-event-resizer,.fc-event:hover .fc-event-resizer{display:block}.fc-event-selected .fc-event-resizer{background:var(--fc-page-bg-color);border-color:inherit;border-radius:calc(var(--fc-event-resizer-dot-total-width)/2);border-style:solid;border-width:var(--fc-event-resizer-dot-border-width);height:var(--fc-event-resizer-dot-total-width);width:var(--fc-event-resizer-dot-total-width)}.fc-event-selected .fc-event-resizer:before{bottom:-20px;content:\"\";left:-20px;position:absolute;right:-20px;top:-20px}.fc-event-selected,.fc-event:focus{box-shadow:0 2px 5px rgba(0,0,0,.2)}.fc-event-selected:before,.fc-event:focus:before{bottom:0;content:\"\";left:0;position:absolute;right:0;top:0;z-index:3}.fc-event-selected:after,.fc-event:focus:after{background:var(--fc-event-selected-overlay-color);bottom:-1px;content:\"\";left:-1px;position:absolute;right:-1px;top:-1px;z-index:1}.fc-h-event{background-color:var(--fc-event-bg-color);border:1px solid var(--fc-event-border-color);display:block}.fc-h-event .fc-event-main{color:var(--fc-event-text-color)}.fc-h-event .fc-event-main-frame{display:flex}.fc-h-event .fc-event-time{max-width:100%;overflow:hidden}.fc-h-event .fc-event-title-container{flex-grow:1;flex-shrink:1;min-width:0}.fc-h-event .fc-event-title{display:inline-block;left:0;max-width:100%;overflow:hidden;right:0;vertical-align:top}.fc-h-event.fc-event-selected:before{bottom:-10px;top:-10px}.fc-direction-ltr .fc-daygrid-block-event:not(.fc-event-start),.fc-direction-rtl .fc-daygrid-block-event:not(.fc-event-end){border-bottom-left-radius:0;border-left-width:0;border-top-left-radius:0}.fc-direction-ltr .fc-daygrid-block-event:not(.fc-event-end),.fc-direction-rtl .fc-daygrid-block-event:not(.fc-event-start){border-bottom-right-radius:0;border-right-width:0;border-top-right-radius:0}.fc-h-event:not(.fc-event-selected) .fc-event-resizer{bottom:0;top:0;width:var(--fc-event-resizer-thickness)}.fc-direction-ltr .fc-h-event:not(.fc-event-selected) .fc-event-resizer-start,.fc-direction-rtl .fc-h-event:not(.fc-event-selected) .fc-event-resizer-end{cursor:w-resize;left:calc(var(--fc-event-resizer-thickness)*-.5)}.fc-direction-ltr .fc-h-event:not(.fc-event-selected) .fc-event-resizer-end,.fc-direction-rtl .fc-h-event:not(.fc-event-selected) .fc-event-resizer-start{cursor:e-resize;right:calc(var(--fc-event-resizer-thickness)*-.5)}.fc-h-event.fc-event-selected .fc-event-resizer{margin-top:calc(var(--fc-event-resizer-dot-total-width)*-.5);top:50%}.fc-direction-ltr .fc-h-event.fc-event-selected .fc-event-resizer-start,.fc-direction-rtl .fc-h-event.fc-event-selected .fc-event-resizer-end{left:calc(var(--fc-event-resizer-dot-total-width)*-.5)}.fc-direction-ltr .fc-h-event.fc-event-selected .fc-event-resizer-end,.fc-direction-rtl .fc-h-event.fc-event-selected .fc-event-resizer-start{right:calc(var(--fc-event-resizer-dot-total-width)*-.5)}.fc .fc-popover{box-shadow:0 2px 6px rgba(0,0,0,.15);position:absolute;z-index:9999}.fc .fc-popover-header{align-items:center;display:flex;flex-direction:row;justify-content:space-between;padding:3px 4px}.fc .fc-popover-title{margin:0 2px}.fc .fc-popover-close{cursor:pointer;font-size:1.1em;opacity:.65}.fc-theme-standard .fc-popover{background:var(--fc-page-bg-color);border:1px solid var(--fc-border-color)}.fc-theme-standard .fc-popover-header{background:var(--fc-neutral-bg-color)}";
    injectStyles(css_248z);

    function removeElement(el) {
        if (el.parentNode) {
            el.parentNode.removeChild(el);
        }
    }
    // Querying
    // ----------------------------------------------------------------------------------------------------------------
    function elementClosest(el, selector) {
        if (el.closest) {
            return el.closest(selector);
            // really bad fallback for IE
            // from https://developer.mozilla.org/en-US/docs/Web/API/Element/closest
        }
        if (!document.documentElement.contains(el)) {
            return null;
        }
        do {
            if (elementMatches(el, selector)) {
                return el;
            }
            el = (el.parentElement || el.parentNode);
        } while (el !== null && el.nodeType === 1);
        return null;
    }
    function elementMatches(el, selector) {
        let method = el.matches || el.matchesSelector || el.msMatchesSelector;
        return method.call(el, selector);
    }
    // accepts multiple subject els
    // returns a real array. good for methods like forEach
    // TODO: accept the document
    function findElements(container, selector) {
        let containers = container instanceof HTMLElement ? [container] : container;
        let allMatches = [];
        for (let i = 0; i < containers.length; i += 1) {
            let matches = containers[i].querySelectorAll(selector);
            for (let j = 0; j < matches.length; j += 1) {
                allMatches.push(matches[j]);
            }
        }
        return allMatches;
    }
    // accepts multiple subject els
    // only queries direct child elements // TODO: rename to findDirectChildren!
    function findDirectChildren(parent, selector) {
        let parents = parent instanceof HTMLElement ? [parent] : parent;
        let allMatches = [];
        for (let i = 0; i < parents.length; i += 1) {
            let childNodes = parents[i].children; // only ever elements
            for (let j = 0; j < childNodes.length; j += 1) {
                let childNode = childNodes[j];
                if (!selector || elementMatches(childNode, selector)) {
                    allMatches.push(childNode);
                }
            }
        }
        return allMatches;
    }
    // Style
    // ----------------------------------------------------------------------------------------------------------------
    const PIXEL_PROP_RE = /(top|left|right|bottom|width|height)$/i;
    function applyStyle(el, props) {
        for (let propName in props) {
            applyStyleProp(el, propName, props[propName]);
        }
    }
    function applyStyleProp(el, name, val) {
        if (val == null) {
            el.style[name] = '';
        }
        else if (typeof val === 'number' && PIXEL_PROP_RE.test(name)) {
            el.style[name] = `${val}px`;
        }
        else {
            el.style[name] = val;
        }
    }
    // Event Handling
    // ----------------------------------------------------------------------------------------------------------------
    // if intercepting bubbled events at the document/window/body level,
    // and want to see originating element (the 'target'), use this util instead
    // of `ev.target` because it goes within web-component boundaries.
    function getEventTargetViaRoot(ev) {
        var _a, _b;
        return (_b = (_a = ev.composedPath) === null || _a === void 0 ? void 0 : _a.call(ev)[0]) !== null && _b !== void 0 ? _b : ev.target;
    }
    // Unique ID for DOM attribute
    let guid$1 = 0;
    function getUniqueDomId() {
        guid$1 += 1;
        return 'fc-dom-' + guid$1;
    }

    // Stops a mouse/touch event from doing it's native browser action
    function preventDefault(ev) {
        ev.preventDefault();
    }
    // Event Delegation
    // ----------------------------------------------------------------------------------------------------------------
    function buildDelegationHandler(selector, handler) {
        return (ev) => {
            let matchedChild = elementClosest(ev.target, selector);
            if (matchedChild) {
                handler.call(matchedChild, ev, matchedChild);
            }
        };
    }
    function listenBySelector(container, eventType, selector, handler) {
        let attachedHandler = buildDelegationHandler(selector, handler);
        container.addEventListener(eventType, attachedHandler);
        return () => {
            container.removeEventListener(eventType, attachedHandler);
        };
    }
    function listenToHoverBySelector(container, selector, onMouseEnter, onMouseLeave) {
        let currentMatchedChild;
        return listenBySelector(container, 'mouseover', selector, (mouseOverEv, matchedChild) => {
            if (matchedChild !== currentMatchedChild) {
                currentMatchedChild = matchedChild;
                onMouseEnter(mouseOverEv, matchedChild);
                let realOnMouseLeave = (mouseLeaveEv) => {
                    currentMatchedChild = null;
                    onMouseLeave(mouseLeaveEv, matchedChild);
                    matchedChild.removeEventListener('mouseleave', realOnMouseLeave);
                };
                // listen to the next mouseleave, and then unattach
                matchedChild.addEventListener('mouseleave', realOnMouseLeave);
            }
        });
    }
    // Animation
    // ----------------------------------------------------------------------------------------------------------------
    const transitionEventNames = [
        'webkitTransitionEnd',
        'otransitionend',
        'oTransitionEnd',
        'msTransitionEnd',
        'transitionend',
    ];
    // triggered only when the next single subsequent transition finishes
    function whenTransitionDone(el, callback) {
        let realCallback = (ev) => {
            callback(ev);
            transitionEventNames.forEach((eventName) => {
                el.removeEventListener(eventName, realCallback);
            });
        };
        transitionEventNames.forEach((eventName) => {
            el.addEventListener(eventName, realCallback); // cross-browser way to determine when the transition finishes
        });
    }
    // ARIA workarounds
    // ----------------------------------------------------------------------------------------------------------------
    function createAriaClickAttrs(handler) {
        return Object.assign({ onClick: handler }, createAriaKeyboardAttrs(handler));
    }
    function createAriaKeyboardAttrs(handler) {
        return {
            tabIndex: 0,
            onKeyDown(ev) {
                if (ev.key === 'Enter' || ev.key === ' ') {
                    handler(ev);
                    ev.preventDefault(); // if space, don't scroll down page
                }
            },
        };
    }

    let guidNumber = 0;
    function guid() {
        guidNumber += 1;
        return String(guidNumber);
    }
    /* FullCalendar-specific DOM Utilities
    ----------------------------------------------------------------------------------------------------------------------*/
    // Make the mouse cursor express that an event is not allowed in the current area
    function disableCursor() {
        document.body.classList.add('fc-not-allowed');
    }
    // Returns the mouse cursor to its original look
    function enableCursor() {
        document.body.classList.remove('fc-not-allowed');
    }
    /* Selection
    ----------------------------------------------------------------------------------------------------------------------*/
    function preventSelection(el) {
        el.style.userSelect = 'none';
        el.style.webkitUserSelect = 'none';
        el.addEventListener('selectstart', preventDefault);
    }
    function allowSelection(el) {
        el.style.userSelect = '';
        el.style.webkitUserSelect = '';
        el.removeEventListener('selectstart', preventDefault);
    }
    /* Context Menu
    ----------------------------------------------------------------------------------------------------------------------*/
    function preventContextMenu(el) {
        el.addEventListener('contextmenu', preventDefault);
    }
    function allowContextMenu(el) {
        el.removeEventListener('contextmenu', preventDefault);
    }
    function parseFieldSpecs(input) {
        let specs = [];
        let tokens = [];
        let i;
        let token;
        if (typeof input === 'string') {
            tokens = input.split(/\s*,\s*/);
        }
        else if (typeof input === 'function') {
            tokens = [input];
        }
        else if (Array.isArray(input)) {
            tokens = input;
        }
        for (i = 0; i < tokens.length; i += 1) {
            token = tokens[i];
            if (typeof token === 'string') {
                specs.push(token.charAt(0) === '-' ?
                    { field: token.substring(1), order: -1 } :
                    { field: token, order: 1 });
            }
            else if (typeof token === 'function') {
                specs.push({ func: token });
            }
        }
        return specs;
    }
    function compareByFieldSpecs(obj0, obj1, fieldSpecs) {
        let i;
        let cmp;
        for (i = 0; i < fieldSpecs.length; i += 1) {
            cmp = compareByFieldSpec(obj0, obj1, fieldSpecs[i]);
            if (cmp) {
                return cmp;
            }
        }
        return 0;
    }
    function compareByFieldSpec(obj0, obj1, fieldSpec) {
        if (fieldSpec.func) {
            return fieldSpec.func(obj0, obj1);
        }
        return flexibleCompare(obj0[fieldSpec.field], obj1[fieldSpec.field])
            * (fieldSpec.order || 1);
    }
    function flexibleCompare(a, b) {
        if (!a && !b) {
            return 0;
        }
        if (b == null) {
            return -1;
        }
        if (a == null) {
            return 1;
        }
        if (typeof a === 'string' || typeof b === 'string') {
            return String(a).localeCompare(String(b));
        }
        return a - b;
    }
    /* String Utilities
    ----------------------------------------------------------------------------------------------------------------------*/
    function padStart(val, len) {
        let s = String(val);
        return '000'.substr(0, len - s.length) + s;
    }
    function formatWithOrdinals(formatter, args, fallbackText) {
        if (typeof formatter === 'function') {
            return formatter(...args);
        }
        if (typeof formatter === 'string') { // non-blank string
            return args.reduce((str, arg, index) => (str.replace('$' + index, arg || '')), formatter);
        }
        return fallbackText;
    }
    /* Number Utilities
    ----------------------------------------------------------------------------------------------------------------------*/
    function compareNumbers(a, b) {
        return a - b;
    }
    function isInt(n) {
        return n % 1 === 0;
    }
    /* FC-specific DOM dimension stuff
    ----------------------------------------------------------------------------------------------------------------------*/
    function computeSmallestCellWidth(cellEl) {
        let allWidthEl = cellEl.querySelector('.fc-scrollgrid-shrink-frame');
        let contentWidthEl = cellEl.querySelector('.fc-scrollgrid-shrink-cushion');
        if (!allWidthEl) {
            throw new Error('needs fc-scrollgrid-shrink-frame className'); // TODO: use const
        }
        if (!contentWidthEl) {
            throw new Error('needs fc-scrollgrid-shrink-cushion className');
        }
        return cellEl.getBoundingClientRect().width - allWidthEl.getBoundingClientRect().width + // the cell padding+border
            contentWidthEl.getBoundingClientRect().width;
    }

    const INTERNAL_UNITS = ['years', 'months', 'days', 'milliseconds'];
    const PARSE_RE = /^(-?)(?:(\d+)\.)?(\d+):(\d\d)(?::(\d\d)(?:\.(\d\d\d))?)?/;
    // Parsing and Creation
    function createDuration(input, unit) {
        if (typeof input === 'string') {
            return parseString(input);
        }
        if (typeof input === 'object' && input) { // non-null object
            return parseObject(input);
        }
        if (typeof input === 'number') {
            return parseObject({ [unit || 'milliseconds']: input });
        }
        return null;
    }
    function parseString(s) {
        let m = PARSE_RE.exec(s);
        if (m) {
            let sign = m[1] ? -1 : 1;
            return {
                years: 0,
                months: 0,
                days: sign * (m[2] ? parseInt(m[2], 10) : 0),
                milliseconds: sign * ((m[3] ? parseInt(m[3], 10) : 0) * 60 * 60 * 1000 + // hours
                    (m[4] ? parseInt(m[4], 10) : 0) * 60 * 1000 + // minutes
                    (m[5] ? parseInt(m[5], 10) : 0) * 1000 + // seconds
                    (m[6] ? parseInt(m[6], 10) : 0) // ms
                ),
            };
        }
        return null;
    }
    function parseObject(obj) {
        let duration = {
            years: obj.years || obj.year || 0,
            months: obj.months || obj.month || 0,
            days: obj.days || obj.day || 0,
            milliseconds: (obj.hours || obj.hour || 0) * 60 * 60 * 1000 + // hours
                (obj.minutes || obj.minute || 0) * 60 * 1000 + // minutes
                (obj.seconds || obj.second || 0) * 1000 + // seconds
                (obj.milliseconds || obj.millisecond || obj.ms || 0), // ms
        };
        let weeks = obj.weeks || obj.week;
        if (weeks) {
            duration.days += weeks * 7;
            duration.specifiedWeeks = true;
        }
        return duration;
    }
    // Equality
    function durationsEqual(d0, d1) {
        return d0.years === d1.years &&
            d0.months === d1.months &&
            d0.days === d1.days &&
            d0.milliseconds === d1.milliseconds;
    }
    function asCleanDays(dur) {
        if (!dur.years && !dur.months && !dur.milliseconds) {
            return dur.days;
        }
        return 0;
    }
    // Simple Math
    function addDurations(d0, d1) {
        return {
            years: d0.years + d1.years,
            months: d0.months + d1.months,
            days: d0.days + d1.days,
            milliseconds: d0.milliseconds + d1.milliseconds,
        };
    }
    function subtractDurations(d1, d0) {
        return {
            years: d1.years - d0.years,
            months: d1.months - d0.months,
            days: d1.days - d0.days,
            milliseconds: d1.milliseconds - d0.milliseconds,
        };
    }
    function multiplyDuration(d, n) {
        return {
            years: d.years * n,
            months: d.months * n,
            days: d.days * n,
            milliseconds: d.milliseconds * n,
        };
    }
    // Conversions
    // "Rough" because they are based on average-case Gregorian months/years
    function asRoughYears(dur) {
        return asRoughDays(dur) / 365;
    }
    function asRoughMonths(dur) {
        return asRoughDays(dur) / 30;
    }
    function asRoughDays(dur) {
        return asRoughMs(dur) / 864e5;
    }
    function asRoughMinutes(dur) {
        return asRoughMs(dur) / (1000 * 60);
    }
    function asRoughSeconds(dur) {
        return asRoughMs(dur) / 1000;
    }
    function asRoughMs(dur) {
        return dur.years * (365 * 864e5) +
            dur.months * (30 * 864e5) +
            dur.days * 864e5 +
            dur.milliseconds;
    }
    // Advanced Math
    function wholeDivideDurations(numerator, denominator) {
        let res = null;
        for (let i = 0; i < INTERNAL_UNITS.length; i += 1) {
            let unit = INTERNAL_UNITS[i];
            if (denominator[unit]) {
                let localRes = numerator[unit] / denominator[unit];
                if (!isInt(localRes) || (res !== null && res !== localRes)) {
                    return null;
                }
                res = localRes;
            }
            else if (numerator[unit]) {
                // needs to divide by something but can't!
                return null;
            }
        }
        return res;
    }
    function greatestDurationDenominator(dur) {
        let ms = dur.milliseconds;
        if (ms) {
            if (ms % 1000 !== 0) {
                return { unit: 'millisecond', value: ms };
            }
            if (ms % (1000 * 60) !== 0) {
                return { unit: 'second', value: ms / 1000 };
            }
            if (ms % (1000 * 60 * 60) !== 0) {
                return { unit: 'minute', value: ms / (1000 * 60) };
            }
            if (ms) {
                return { unit: 'hour', value: ms / (1000 * 60 * 60) };
            }
        }
        if (dur.days) {
            if (dur.specifiedWeeks && dur.days % 7 === 0) {
                return { unit: 'week', value: dur.days / 7 };
            }
            return { unit: 'day', value: dur.days };
        }
        if (dur.months) {
            return { unit: 'month', value: dur.months };
        }
        if (dur.years) {
            return { unit: 'year', value: dur.years };
        }
        return { unit: 'millisecond', value: 0 };
    }

    const { hasOwnProperty } = Object.prototype;
    // Merges an array of objects into a single object.
    // The second argument allows for an array of property names who's object values will be merged together.
    function mergeProps(propObjs, complexPropsMap) {
        let dest = {};
        if (complexPropsMap) {
            for (let name in complexPropsMap) {
                if (complexPropsMap[name] === isMaybeObjectsEqual) { // implies that it's object-mergeable
                    let complexObjs = [];
                    // collect the trailing object values, stopping when a non-object is discovered
                    for (let i = propObjs.length - 1; i >= 0; i -= 1) {
                        let val = propObjs[i][name];
                        if (typeof val === 'object' && val) { // non-null object
                            complexObjs.unshift(val);
                        }
                        else if (val !== undefined) {
                            dest[name] = val; // if there were no objects, this value will be used
                            break;
                        }
                    }
                    // if the trailing values were objects, use the merged value
                    if (complexObjs.length) {
                        dest[name] = mergeProps(complexObjs);
                    }
                }
            }
        }
        // copy values into the destination, going from last to first
        for (let i = propObjs.length - 1; i >= 0; i -= 1) {
            let props = propObjs[i];
            for (let name in props) {
                if (!(name in dest)) { // if already assigned by previous props or complex props, don't reassign
                    dest[name] = props[name];
                }
            }
        }
        return dest;
    }
    function filterHash(hash, func) {
        let filtered = {};
        for (let key in hash) {
            if (func(hash[key], key)) {
                filtered[key] = hash[key];
            }
        }
        return filtered;
    }
    function mapHash(hash, func) {
        let newHash = {};
        for (let key in hash) {
            newHash[key] = func(hash[key], key);
        }
        return newHash;
    }
    function arrayToHash(a) {
        let hash = {};
        for (let item of a) {
            hash[item] = true;
        }
        return hash;
    }
    // TODO: reassess browser support
    // https://caniuse.com/?search=object.values
    function hashValuesToArray(obj) {
        let a = [];
        for (let key in obj) {
            a.push(obj[key]);
        }
        return a;
    }
    function isPropsEqual(obj0, obj1) {
        if (obj0 === obj1) {
            return true;
        }
        for (let key in obj0) {
            if (hasOwnProperty.call(obj0, key)) {
                if (!(key in obj1)) {
                    return false;
                }
            }
        }
        for (let key in obj1) {
            if (hasOwnProperty.call(obj1, key)) {
                if (obj0[key] !== obj1[key]) {
                    return false;
                }
            }
        }
        return true;
    }
    const HANDLER_RE = /^on[A-Z]/;
    function isNonHandlerPropsEqual(obj0, obj1) {
        const keys = getUnequalProps(obj0, obj1);
        for (let key of keys) {
            if (!HANDLER_RE.test(key)) {
                return false;
            }
        }
        return true;
    }
    function getUnequalProps(obj0, obj1) {
        let keys = [];
        for (let key in obj0) {
            if (hasOwnProperty.call(obj0, key)) {
                if (!(key in obj1)) {
                    keys.push(key);
                }
            }
        }
        for (let key in obj1) {
            if (hasOwnProperty.call(obj1, key)) {
                if (obj0[key] !== obj1[key]) {
                    keys.push(key);
                }
            }
        }
        return keys;
    }
    function compareObjs(oldProps, newProps, equalityFuncs = {}) {
        if (oldProps === newProps) {
            return true;
        }
        // if (debug) {
        //   for (let key in newProps) {
        //     if (key in oldProps && isObjValsEqual(oldProps[key], newProps[key], equalityFuncs[key])) {
        //       // equal
        //     } else {
        //       if (debug) {
        //         console.log('prop difference', key, oldProps[key], newProps[key])
        //       }
        //     }
        //   }
        //   // check for props that were omitted in the new
        //   for (let key in oldProps) {
        //     if (!(key in newProps)) {
        //       if (debug) {
        //         console.log('prop absent', key)
        //       }
        //     }
        //   }
        // }
        for (let key in newProps) {
            if (key in oldProps && isObjValsEqual(oldProps[key], newProps[key], equalityFuncs[key])) ;
            else {
                return false;
            }
        }
        // check for props that were omitted in the new
        for (let key in oldProps) {
            if (!(key in newProps)) {
                return false;
            }
        }
        return true;
    }
    /*
    assumed "true" equality for handler names like "onReceiveSomething"
    */
    function isObjValsEqual(val0, val1, comparator) {
        if (val0 === val1 || comparator === true) {
            return true;
        }
        if (comparator) {
            return comparator(val0, val1);
        }
        return false;
    }
    function collectFromHash(hash, startIndex = 0, endIndex, step = 1) {
        let res = [];
        if (endIndex == null) {
            endIndex = Object.keys(hash).length;
        }
        for (let i = startIndex; i < endIndex; i += step) {
            let val = hash[i];
            if (val !== undefined) { // will disregard undefined for sparse arrays
                res.push(val);
            }
        }
        return res;
    }

    // TODO: new util arrayify?
    function removeExact(array, exactVal) {
        let removeCnt = 0;
        let i = 0;
        while (i < array.length) {
            if (array[i] === exactVal) {
                array.splice(i, 1);
                removeCnt += 1;
            }
            else {
                i += 1;
            }
        }
        return removeCnt;
    }
    function isArraysEqual(a0, a1, equalityFunc) {
        if (a0 === a1) {
            return true;
        }
        let len = a0.length;
        let i;
        if (len !== a1.length) { // not array? or not same length?
            return false;
        }
        for (i = 0; i < len; i += 1) {
            if (!(equalityFunc ? equalityFunc(a0[i], a1[i]) : a0[i] === a1[i])) {
                return false;
            }
        }
        return true;
    }

    const DAY_IDS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    // Adding
    function addWeeks(m, n) {
        let a = dateToUtcArray(m);
        a[2] += n * 7;
        return arrayToUtcDate(a);
    }
    function addDays(m, n) {
        let a = dateToUtcArray(m);
        a[2] += n;
        return arrayToUtcDate(a);
    }
    function addMs(m, n) {
        let a = dateToUtcArray(m);
        a[6] += n;
        return arrayToUtcDate(a);
    }
    // Diffing (all return floats)
    // TODO: why not use ranges?
    function diffWeeks(m0, m1) {
        return diffDays(m0, m1) / 7;
    }
    function diffDays(m0, m1) {
        return (m1.valueOf() - m0.valueOf()) / (1000 * 60 * 60 * 24);
    }
    function diffHours(m0, m1) {
        return (m1.valueOf() - m0.valueOf()) / (1000 * 60 * 60);
    }
    function diffMinutes(m0, m1) {
        return (m1.valueOf() - m0.valueOf()) / (1000 * 60);
    }
    function diffSeconds(m0, m1) {
        return (m1.valueOf() - m0.valueOf()) / 1000;
    }
    function diffDayAndTime(m0, m1) {
        let m0day = startOfDay(m0);
        let m1day = startOfDay(m1);
        return {
            years: 0,
            months: 0,
            days: Math.round(diffDays(m0day, m1day)),
            milliseconds: (m1.valueOf() - m1day.valueOf()) - (m0.valueOf() - m0day.valueOf()),
        };
    }
    // Diffing Whole Units
    function diffWholeWeeks(m0, m1) {
        let d = diffWholeDays(m0, m1);
        if (d !== null && d % 7 === 0) {
            return d / 7;
        }
        return null;
    }
    function diffWholeDays(m0, m1) {
        if (timeAsMs(m0) === timeAsMs(m1)) {
            return Math.round(diffDays(m0, m1));
        }
        return null;
    }
    // Start-Of
    function startOfDay(m) {
        return arrayToUtcDate([
            m.getUTCFullYear(),
            m.getUTCMonth(),
            m.getUTCDate(),
        ]);
    }
    function startOfHour(m) {
        return arrayToUtcDate([
            m.getUTCFullYear(),
            m.getUTCMonth(),
            m.getUTCDate(),
            m.getUTCHours(),
        ]);
    }
    function startOfMinute(m) {
        return arrayToUtcDate([
            m.getUTCFullYear(),
            m.getUTCMonth(),
            m.getUTCDate(),
            m.getUTCHours(),
            m.getUTCMinutes(),
        ]);
    }
    function startOfSecond(m) {
        return arrayToUtcDate([
            m.getUTCFullYear(),
            m.getUTCMonth(),
            m.getUTCDate(),
            m.getUTCHours(),
            m.getUTCMinutes(),
            m.getUTCSeconds(),
        ]);
    }
    // Week Computation
    function weekOfYear(marker, dow, doy) {
        let y = marker.getUTCFullYear();
        let w = weekOfGivenYear(marker, y, dow, doy);
        if (w < 1) {
            return weekOfGivenYear(marker, y - 1, dow, doy);
        }
        let nextW = weekOfGivenYear(marker, y + 1, dow, doy);
        if (nextW >= 1) {
            return Math.min(w, nextW);
        }
        return w;
    }
    function weekOfGivenYear(marker, year, dow, doy) {
        let firstWeekStart = arrayToUtcDate([year, 0, 1 + firstWeekOffset(year, dow, doy)]);
        let dayStart = startOfDay(marker);
        let days = Math.round(diffDays(firstWeekStart, dayStart));
        return Math.floor(days / 7) + 1; // zero-indexed
    }
    // start-of-first-week - start-of-year
    function firstWeekOffset(year, dow, doy) {
        // first-week day -- which january is always in the first week (4 for iso, 1 for other)
        let fwd = 7 + dow - doy;
        // first-week day local weekday -- which local weekday is fwd
        let fwdlw = (7 + arrayToUtcDate([year, 0, fwd]).getUTCDay() - dow) % 7;
        return -fwdlw + fwd - 1;
    }
    // Array Conversion
    function dateToLocalArray(date) {
        return [
            date.getFullYear(),
            date.getMonth(),
            date.getDate(),
            date.getHours(),
            date.getMinutes(),
            date.getSeconds(),
            date.getMilliseconds(),
        ];
    }
    function arrayToLocalDate(a) {
        return new Date(a[0], a[1] || 0, a[2] == null ? 1 : a[2], // day of month
        a[3] || 0, a[4] || 0, a[5] || 0);
    }
    function dateToUtcArray(date) {
        return [
            date.getUTCFullYear(),
            date.getUTCMonth(),
            date.getUTCDate(),
            date.getUTCHours(),
            date.getUTCMinutes(),
            date.getUTCSeconds(),
            date.getUTCMilliseconds(),
        ];
    }
    function arrayToUtcDate(a) {
        // according to web standards (and Safari), a month index is required.
        // massage if only given a year.
        if (a.length === 1) {
            a = a.concat([0]);
        }
        return new Date(Date.UTC(...a));
    }
    // Other Utils
    function isValidDate(m) {
        return !isNaN(m.valueOf());
    }
    function timeAsMs(m) {
        return m.getUTCHours() * 1000 * 60 * 60 +
            m.getUTCMinutes() * 1000 * 60 +
            m.getUTCSeconds() * 1000 +
            m.getUTCMilliseconds();
    }

    // timeZoneOffset is in minutes
    function buildIsoString(marker, timeZoneOffset, stripZeroTime = false) {
        let s = marker.toISOString();
        s = s.replace('.000', '');
        if (stripZeroTime) {
            s = s.replace('T00:00:00Z', '');
        }
        if (s.length > 10) { // time part wasn't stripped, can add timezone info
            if (timeZoneOffset == null) {
                s = s.replace('Z', '');
            }
            else if (timeZoneOffset !== 0) {
                s = s.replace('Z', formatTimeZoneOffset(timeZoneOffset, true));
            }
            // otherwise, its UTC-0 and we want to keep the Z
        }
        return s;
    }
    // formats the date, but with no time part
    // TODO: somehow merge with buildIsoString and stripZeroTime
    // TODO: rename. omit "string"
    function formatDayString(marker) {
        return marker.toISOString().replace(/T.*$/, '');
    }
    function formatIsoMonthStr(marker) {
        return marker.toISOString().match(/^\d{4}-\d{2}/)[0];
    }
    // TODO: use Date::toISOString and use everything after the T?
    function formatIsoTimeString(marker) {
        return padStart(marker.getUTCHours(), 2) + ':' +
            padStart(marker.getUTCMinutes(), 2) + ':' +
            padStart(marker.getUTCSeconds(), 2);
    }
    function formatTimeZoneOffset(minutes, doIso = false) {
        let sign = minutes < 0 ? '-' : '+';
        let abs = Math.abs(minutes);
        let hours = Math.floor(abs / 60);
        let mins = Math.round(abs % 60);
        if (doIso) {
            return `${sign + padStart(hours, 2)}:${padStart(mins, 2)}`;
        }
        return `GMT${sign}${hours}${mins ? `:${padStart(mins, 2)}` : ''}`;
    }

    function memoize(workerFunc, resEquality, teardownFunc) {
        let currentArgs;
        let currentRes;
        return function (...newArgs) {
            if (!currentArgs) {
                currentRes = workerFunc.apply(this, newArgs);
            }
            else if (!isArraysEqual(currentArgs, newArgs)) {
                if (teardownFunc) {
                    teardownFunc(currentRes);
                }
                let res = workerFunc.apply(this, newArgs);
                if (!resEquality || !resEquality(res, currentRes)) {
                    currentRes = res;
                }
            }
            currentArgs = newArgs;
            return currentRes;
        };
    }
    function memoizeObjArg(workerFunc, resEquality, teardownFunc) {
        let currentArg;
        let currentRes;
        return (newArg) => {
            if (!currentArg) {
                currentRes = workerFunc.call(this, newArg);
            }
            else if (!isPropsEqual(currentArg, newArg)) {
                if (teardownFunc) {
                    teardownFunc(currentRes);
                }
                let res = workerFunc.call(this, newArg);
                if (!resEquality || !resEquality(res, currentRes)) {
                    currentRes = res;
                }
            }
            currentArg = newArg;
            return currentRes;
        };
    }
    function memoizeArraylike(// used at all?
    workerFunc, resEquality, teardownFunc) {
        let currentArgSets = [];
        let currentResults = [];
        return (newArgSets) => {
            let currentLen = currentArgSets.length;
            let newLen = newArgSets.length;
            let i = 0;
            for (; i < currentLen; i += 1) {
                if (!newArgSets[i]) { // one of the old sets no longer exists
                    if (teardownFunc) {
                        teardownFunc(currentResults[i]);
                    }
                }
                else if (!isArraysEqual(currentArgSets[i], newArgSets[i])) {
                    if (teardownFunc) {
                        teardownFunc(currentResults[i]);
                    }
                    let res = workerFunc.apply(this, newArgSets[i]);
                    if (!resEquality || !resEquality(res, currentResults[i])) {
                        currentResults[i] = res;
                    }
                }
            }
            for (; i < newLen; i += 1) {
                currentResults[i] = workerFunc.apply(this, newArgSets[i]);
            }
            currentArgSets = newArgSets;
            currentResults.splice(newLen); // remove excess
            return currentResults;
        };
    }
    function memoizeHashlike(workerFunc, resEquality, teardownFunc) {
        let currentArgHash = {};
        let currentResHash = {};
        return (newArgHash) => {
            let newResHash = {};
            for (let key in newArgHash) {
                if (!currentResHash[key]) {
                    newResHash[key] = workerFunc.apply(this, newArgHash[key]);
                }
                else if (!isArraysEqual(currentArgHash[key], newArgHash[key])) {
                    if (teardownFunc) {
                        teardownFunc(currentResHash[key]);
                    }
                    let res = workerFunc.apply(this, newArgHash[key]);
                    newResHash[key] = (resEquality && resEquality(res, currentResHash[key]))
                        ? currentResHash[key]
                        : res;
                }
                else {
                    newResHash[key] = currentResHash[key];
                }
            }
            currentArgHash = newArgHash;
            currentResHash = newResHash;
            return newResHash;
        };
    }

    const EXTENDED_SETTINGS_AND_SEVERITIES = {
        week: 3,
        separator: 9,
        omitZeroMinute: 9,
        meridiem: 9,
        omitCommas: 9,
    };
    const STANDARD_DATE_PROP_SEVERITIES = {
        timeZoneName: 7,
        era: 6,
        year: 5,
        month: 4,
        day: 2,
        weekday: 2,
        hour: 1,
        minute: 1,
        second: 1,
    };
    const MERIDIEM_RE = /\s*([ap])\.?m\.?/i; // eats up leading spaces too
    const COMMA_RE = /,/g; // we need re for globalness
    const MULTI_SPACE_RE = /\s+/g;
    const LTR_RE = /\u200e/g; // control character
    const UTC_RE = /UTC|GMT/;
    class NativeFormatter {
        constructor(formatSettings) {
            let standardDateProps = {};
            let extendedSettings = {};
            let smallestUnitNum = 9; // the smallest unit in the formatter (9 is a sentinel, beyond max)
            for (let name in formatSettings) {
                if (name in EXTENDED_SETTINGS_AND_SEVERITIES) {
                    extendedSettings[name] = formatSettings[name];
                    const severity = EXTENDED_SETTINGS_AND_SEVERITIES[name];
                    if (severity < 9) {
                        smallestUnitNum = Math.min(EXTENDED_SETTINGS_AND_SEVERITIES[name], smallestUnitNum);
                    }
                }
                else {
                    standardDateProps[name] = formatSettings[name];
                    if (name in STANDARD_DATE_PROP_SEVERITIES) { // TODO: what about hour12? no severity
                        smallestUnitNum = Math.min(STANDARD_DATE_PROP_SEVERITIES[name], smallestUnitNum);
                    }
                }
            }
            this.standardDateProps = standardDateProps;
            this.extendedSettings = extendedSettings;
            this.smallestUnitNum = smallestUnitNum;
            this.buildFormattingFunc = memoize(buildFormattingFunc);
        }
        format(date, context) {
            return this.buildFormattingFunc(this.standardDateProps, this.extendedSettings, context)(date);
        }
        formatRange(start, end, context, betterDefaultSeparator) {
            let { standardDateProps, extendedSettings } = this;
            let diffSeverity = computeMarkerDiffSeverity(start.marker, end.marker, context.calendarSystem);
            if (!diffSeverity) {
                return this.format(start, context);
            }
            let biggestUnitForPartial = diffSeverity;
            if (biggestUnitForPartial > 1 && // the two dates are different in a way that's larger scale than time
                (standardDateProps.year === 'numeric' || standardDateProps.year === '2-digit') &&
                (standardDateProps.month === 'numeric' || standardDateProps.month === '2-digit') &&
                (standardDateProps.day === 'numeric' || standardDateProps.day === '2-digit')) {
                biggestUnitForPartial = 1; // make it look like the dates are only different in terms of time
            }
            let full0 = this.format(start, context);
            let full1 = this.format(end, context);
            if (full0 === full1) {
                return full0;
            }
            let partialDateProps = computePartialFormattingOptions(standardDateProps, biggestUnitForPartial);
            let partialFormattingFunc = buildFormattingFunc(partialDateProps, extendedSettings, context);
            let partial0 = partialFormattingFunc(start);
            let partial1 = partialFormattingFunc(end);
            let insertion = findCommonInsertion(full0, partial0, full1, partial1);
            let separator = extendedSettings.separator || betterDefaultSeparator || context.defaultSeparator || '';
            if (insertion) {
                return insertion.before + partial0 + separator + partial1 + insertion.after;
            }
            return full0 + separator + full1;
        }
        getSmallestUnit() {
            switch (this.smallestUnitNum) {
                case 7:
                case 6:
                case 5:
                    return 'year';
                case 4:
                    return 'month';
                case 3:
                    return 'week';
                case 2:
                    return 'day';
                default:
                    return 'time'; // really?
            }
        }
    }
    function buildFormattingFunc(standardDateProps, extendedSettings, context) {
        let standardDatePropCnt = Object.keys(standardDateProps).length;
        if (standardDatePropCnt === 1 && standardDateProps.timeZoneName === 'short') {
            return (date) => (formatTimeZoneOffset(date.timeZoneOffset));
        }
        if (standardDatePropCnt === 0 && extendedSettings.week) {
            return (date) => (formatWeekNumber(context.computeWeekNumber(date.marker), context.weekText, context.weekTextLong, context.locale, extendedSettings.week));
        }
        return buildNativeFormattingFunc(standardDateProps, extendedSettings, context);
    }
    function buildNativeFormattingFunc(standardDateProps, extendedSettings, context) {
        standardDateProps = Object.assign({}, standardDateProps); // copy
        extendedSettings = Object.assign({}, extendedSettings); // copy
        sanitizeSettings(standardDateProps, extendedSettings);
        standardDateProps.timeZone = 'UTC'; // we leverage the only guaranteed timeZone for our UTC markers
        let normalFormat = new Intl.DateTimeFormat(context.locale.codes, standardDateProps);
        let zeroFormat; // needed?
        if (extendedSettings.omitZeroMinute) {
            let zeroProps = Object.assign({}, standardDateProps);
            delete zeroProps.minute; // seconds and ms were already considered in sanitizeSettings
            zeroFormat = new Intl.DateTimeFormat(context.locale.codes, zeroProps);
        }
        return (date) => {
            let { marker } = date;
            let format;
            if (zeroFormat && !marker.getUTCMinutes()) {
                format = zeroFormat;
            }
            else {
                format = normalFormat;
            }
            let s = format.format(marker);
            return postProcess(s, date, standardDateProps, extendedSettings, context);
        };
    }
    function sanitizeSettings(standardDateProps, extendedSettings) {
        // deal with a browser inconsistency where formatting the timezone
        // requires that the hour/minute be present.
        if (standardDateProps.timeZoneName) {
            if (!standardDateProps.hour) {
                standardDateProps.hour = '2-digit';
            }
            if (!standardDateProps.minute) {
                standardDateProps.minute = '2-digit';
            }
        }
        // only support short timezone names
        if (standardDateProps.timeZoneName === 'long') {
            standardDateProps.timeZoneName = 'short';
        }
        // if requesting to display seconds, MUST display minutes
        if (extendedSettings.omitZeroMinute && (standardDateProps.second || standardDateProps.millisecond)) {
            delete extendedSettings.omitZeroMinute;
        }
    }
    function postProcess(s, date, standardDateProps, extendedSettings, context) {
        s = s.replace(LTR_RE, ''); // remove left-to-right control chars. do first. good for other regexes
        if (standardDateProps.timeZoneName === 'short') {
            s = injectTzoStr(s, (context.timeZone === 'UTC' || date.timeZoneOffset == null) ?
                'UTC' : // important to normalize for IE, which does "GMT"
                formatTimeZoneOffset(date.timeZoneOffset));
        }
        if (extendedSettings.omitCommas) {
            s = s.replace(COMMA_RE, '').trim();
        }
        if (extendedSettings.omitZeroMinute) {
            s = s.replace(':00', ''); // zeroFormat doesn't always achieve this
        }
        // ^ do anything that might create adjacent spaces before this point,
        // because MERIDIEM_RE likes to eat up loading spaces
        if (extendedSettings.meridiem === false) {
            s = s.replace(MERIDIEM_RE, '').trim();
        }
        else if (extendedSettings.meridiem === 'narrow') { // a/p
            s = s.replace(MERIDIEM_RE, (m0, m1) => m1.toLocaleLowerCase());
        }
        else if (extendedSettings.meridiem === 'short') { // am/pm
            s = s.replace(MERIDIEM_RE, (m0, m1) => `${m1.toLocaleLowerCase()}m`);
        }
        else if (extendedSettings.meridiem === 'lowercase') { // other meridiem transformers already converted to lowercase
            s = s.replace(MERIDIEM_RE, (m0) => m0.toLocaleLowerCase());
        }
        s = s.replace(MULTI_SPACE_RE, ' ');
        s = s.trim();
        return s;
    }
    function injectTzoStr(s, tzoStr) {
        let replaced = false;
        s = s.replace(UTC_RE, () => {
            replaced = true;
            return tzoStr;
        });
        // IE11 doesn't include UTC/GMT in the original string, so append to end
        if (!replaced) {
            s += ` ${tzoStr}`;
        }
        return s;
    }
    function formatWeekNumber(num, weekText, weekTextLong, locale, display) {
        let parts = [];
        if (display === 'long') {
            parts.push(weekTextLong);
        }
        else if (display === 'short' || display === 'narrow') {
            parts.push(weekText);
        }
        if (display === 'long' || display === 'short') {
            parts.push(' ');
        }
        parts.push(locale.simpleNumberFormat.format(num));
        if (locale.options.direction === 'rtl') { // TODO: use control characters instead?
            parts.reverse();
        }
        return parts.join('');
    }
    // Range Formatting Utils
    // 0 = exactly the same
    // 1 = different by time
    // and bigger
    function computeMarkerDiffSeverity(d0, d1, ca) {
        if (ca.getMarkerYear(d0) !== ca.getMarkerYear(d1)) {
            return 5;
        }
        if (ca.getMarkerMonth(d0) !== ca.getMarkerMonth(d1)) {
            return 4;
        }
        if (ca.getMarkerDay(d0) !== ca.getMarkerDay(d1)) {
            return 2;
        }
        if (timeAsMs(d0) !== timeAsMs(d1)) {
            return 1;
        }
        return 0;
    }
    function computePartialFormattingOptions(options, biggestUnit) {
        let partialOptions = {};
        for (let name in options) {
            if (!(name in STANDARD_DATE_PROP_SEVERITIES) || // not a date part prop (like timeZone)
                STANDARD_DATE_PROP_SEVERITIES[name] <= biggestUnit) {
                partialOptions[name] = options[name];
            }
        }
        return partialOptions;
    }
    function findCommonInsertion(full0, partial0, full1, partial1) {
        let i0 = 0;
        while (i0 < full0.length) {
            let found0 = full0.indexOf(partial0, i0);
            if (found0 === -1) {
                break;
            }
            let before0 = full0.substr(0, found0);
            i0 = found0 + partial0.length;
            let after0 = full0.substr(i0);
            let i1 = 0;
            while (i1 < full1.length) {
                let found1 = full1.indexOf(partial1, i1);
                if (found1 === -1) {
                    break;
                }
                let before1 = full1.substr(0, found1);
                i1 = found1 + partial1.length;
                let after1 = full1.substr(i1);
                if (before0 === before1 && after0 === after1) {
                    return {
                        before: before0,
                        after: after0,
                    };
                }
            }
        }
        return null;
    }

    function expandZonedMarker(dateInfo, calendarSystem) {
        let a = calendarSystem.markerToArray(dateInfo.marker);
        return {
            marker: dateInfo.marker,
            timeZoneOffset: dateInfo.timeZoneOffset,
            array: a,
            year: a[0],
            month: a[1],
            day: a[2],
            hour: a[3],
            minute: a[4],
            second: a[5],
            millisecond: a[6],
        };
    }

    function createVerboseFormattingArg(start, end, context, betterDefaultSeparator) {
        let startInfo = expandZonedMarker(start, context.calendarSystem);
        let endInfo = end ? expandZonedMarker(end, context.calendarSystem) : null;
        return {
            date: startInfo,
            start: startInfo,
            end: endInfo,
            timeZone: context.timeZone,
            localeCodes: context.locale.codes,
            defaultSeparator: betterDefaultSeparator || context.defaultSeparator,
        };
    }

    /*
    TODO: fix the terminology of "formatter" vs "formatting func"
    */
    /*
    At the time of instantiation, this object does not know which cmd-formatting system it will use.
    It receives this at the time of formatting, as a setting.
    */
    class CmdFormatter {
        constructor(cmdStr) {
            this.cmdStr = cmdStr;
        }
        format(date, context, betterDefaultSeparator) {
            return context.cmdFormatter(this.cmdStr, createVerboseFormattingArg(date, null, context, betterDefaultSeparator));
        }
        formatRange(start, end, context, betterDefaultSeparator) {
            return context.cmdFormatter(this.cmdStr, createVerboseFormattingArg(start, end, context, betterDefaultSeparator));
        }
    }

    class FuncFormatter {
        constructor(func) {
            this.func = func;
        }
        format(date, context, betterDefaultSeparator) {
            return this.func(createVerboseFormattingArg(date, null, context, betterDefaultSeparator));
        }
        formatRange(start, end, context, betterDefaultSeparator) {
            return this.func(createVerboseFormattingArg(start, end, context, betterDefaultSeparator));
        }
    }

    function createFormatter(input) {
        if (typeof input === 'object' && input) { // non-null object
            return new NativeFormatter(input);
        }
        if (typeof input === 'string') {
            return new CmdFormatter(input);
        }
        if (typeof input === 'function') {
            return new FuncFormatter(input);
        }
        return null;
    }

    // base options
    // ------------
    const BASE_OPTION_REFINERS = {
        navLinkDayClick: identity,
        navLinkWeekClick: identity,
        duration: createDuration,
        bootstrapFontAwesome: identity,
        buttonIcons: identity,
        customButtons: identity,
        defaultAllDayEventDuration: createDuration,
        defaultTimedEventDuration: createDuration,
        nextDayThreshold: createDuration,
        scrollTime: createDuration,
        scrollTimeReset: Boolean,
        slotMinTime: createDuration,
        slotMaxTime: createDuration,
        dayPopoverFormat: createFormatter,
        slotDuration: createDuration,
        snapDuration: createDuration,
        headerToolbar: identity,
        footerToolbar: identity,
        defaultRangeSeparator: String,
        titleRangeSeparator: String,
        forceEventDuration: Boolean,
        dayHeaders: Boolean,
        dayHeaderFormat: createFormatter,
        dayHeaderClassNames: identity,
        dayHeaderContent: identity,
        dayHeaderDidMount: identity,
        dayHeaderWillUnmount: identity,
        dayCellClassNames: identity,
        dayCellContent: identity,
        dayCellDidMount: identity,
        dayCellWillUnmount: identity,
        initialView: String,
        aspectRatio: Number,
        weekends: Boolean,
        weekNumberCalculation: identity,
        weekNumbers: Boolean,
        weekNumberClassNames: identity,
        weekNumberContent: identity,
        weekNumberDidMount: identity,
        weekNumberWillUnmount: identity,
        editable: Boolean,
        viewClassNames: identity,
        viewDidMount: identity,
        viewWillUnmount: identity,
        nowIndicator: Boolean,
        nowIndicatorSnap: identity,
        nowIndicatorClassNames: identity,
        nowIndicatorContent: identity,
        nowIndicatorDidMount: identity,
        nowIndicatorWillUnmount: identity,
        showNonCurrentDates: Boolean,
        lazyFetching: Boolean,
        startParam: String,
        endParam: String,
        timeZoneParam: String,
        timeZone: String,
        locales: identity,
        locale: identity,
        themeSystem: String,
        dragRevertDuration: Number,
        dragScroll: Boolean,
        allDayMaintainDuration: Boolean,
        unselectAuto: Boolean,
        dropAccept: identity,
        eventOrder: parseFieldSpecs,
        eventOrderStrict: Boolean,
        handleWindowResize: Boolean,
        windowResizeDelay: Number,
        longPressDelay: Number,
        eventDragMinDistance: Number,
        expandRows: Boolean,
        height: identity,
        contentHeight: identity,
        direction: String,
        weekNumberFormat: createFormatter,
        eventResizableFromStart: Boolean,
        displayEventTime: Boolean,
        displayEventEnd: Boolean,
        weekText: String,
        weekTextLong: String,
        progressiveEventRendering: Boolean,
        businessHours: identity,
        initialDate: identity,
        now: identity,
        eventDataTransform: identity,
        stickyHeaderDates: identity,
        stickyFooterScrollbar: identity,
        viewHeight: identity,
        defaultAllDay: Boolean,
        eventSourceFailure: identity,
        eventSourceSuccess: identity,
        eventDisplay: String,
        eventStartEditable: Boolean,
        eventDurationEditable: Boolean,
        eventOverlap: identity,
        eventConstraint: identity,
        eventAllow: identity,
        eventBackgroundColor: String,
        eventBorderColor: String,
        eventTextColor: String,
        eventColor: String,
        eventClassNames: identity,
        eventContent: identity,
        eventDidMount: identity,
        eventWillUnmount: identity,
        selectConstraint: identity,
        selectOverlap: identity,
        selectAllow: identity,
        droppable: Boolean,
        unselectCancel: String,
        slotLabelFormat: identity,
        slotLaneClassNames: identity,
        slotLaneContent: identity,
        slotLaneDidMount: identity,
        slotLaneWillUnmount: identity,
        slotLabelClassNames: identity,
        slotLabelContent: identity,
        slotLabelDidMount: identity,
        slotLabelWillUnmount: identity,
        dayMaxEvents: identity,
        dayMaxEventRows: identity,
        dayMinWidth: Number,
        slotLabelInterval: createDuration,
        allDayText: String,
        allDayClassNames: identity,
        allDayContent: identity,
        allDayDidMount: identity,
        allDayWillUnmount: identity,
        slotMinWidth: Number,
        navLinks: Boolean,
        eventTimeFormat: createFormatter,
        rerenderDelay: Number,
        moreLinkText: identity,
        moreLinkHint: identity,
        selectMinDistance: Number,
        selectable: Boolean,
        selectLongPressDelay: Number,
        eventLongPressDelay: Number,
        selectMirror: Boolean,
        eventMaxStack: Number,
        eventMinHeight: Number,
        eventMinWidth: Number,
        eventShortHeight: Number,
        slotEventOverlap: Boolean,
        plugins: identity,
        firstDay: Number,
        dayCount: Number,
        dateAlignment: String,
        dateIncrement: createDuration,
        hiddenDays: identity,
        fixedWeekCount: Boolean,
        validRange: identity,
        visibleRange: identity,
        titleFormat: identity,
        eventInteractive: Boolean,
        // only used by list-view, but languages define the value, so we need it in base options
        noEventsText: String,
        viewHint: identity,
        navLinkHint: identity,
        closeHint: String,
        timeHint: String,
        eventHint: String,
        moreLinkClick: identity,
        moreLinkClassNames: identity,
        moreLinkContent: identity,
        moreLinkDidMount: identity,
        moreLinkWillUnmount: identity,
        monthStartFormat: createFormatter,
        // for connectors
        // (can't be part of plugin system b/c must be provided at runtime)
        handleCustomRendering: identity,
        customRenderingMetaMap: identity,
        customRenderingReplaces: Boolean,
    };
    // do NOT give a type here. need `typeof BASE_OPTION_DEFAULTS` to give real results.
    // raw values.
    const BASE_OPTION_DEFAULTS = {
        eventDisplay: 'auto',
        defaultRangeSeparator: ' - ',
        titleRangeSeparator: ' \u2013 ',
        defaultTimedEventDuration: '01:00:00',
        defaultAllDayEventDuration: { day: 1 },
        forceEventDuration: false,
        nextDayThreshold: '00:00:00',
        dayHeaders: true,
        initialView: '',
        aspectRatio: 1.35,
        headerToolbar: {
            start: 'title',
            center: '',
            end: 'today prev,next',
        },
        weekends: true,
        weekNumbers: false,
        weekNumberCalculation: 'local',
        editable: false,
        nowIndicator: false,
        scrollTime: '06:00:00',
        scrollTimeReset: true,
        slotMinTime: '00:00:00',
        slotMaxTime: '24:00:00',
        showNonCurrentDates: true,
        lazyFetching: true,
        startParam: 'start',
        endParam: 'end',
        timeZoneParam: 'timeZone',
        timeZone: 'local',
        locales: [],
        locale: '',
        themeSystem: 'standard',
        dragRevertDuration: 500,
        dragScroll: true,
        allDayMaintainDuration: false,
        unselectAuto: true,
        dropAccept: '*',
        eventOrder: 'start,-duration,allDay,title',
        dayPopoverFormat: { month: 'long', day: 'numeric', year: 'numeric' },
        handleWindowResize: true,
        windowResizeDelay: 100,
        longPressDelay: 1000,
        eventDragMinDistance: 5,
        expandRows: false,
        navLinks: false,
        selectable: false,
        eventMinHeight: 15,
        eventMinWidth: 30,
        eventShortHeight: 30,
        monthStartFormat: { month: 'long', day: 'numeric' },
        nowIndicatorSnap: 'auto',
    };
    // calendar listeners
    // ------------------
    const CALENDAR_LISTENER_REFINERS = {
        datesSet: identity,
        eventsSet: identity,
        eventAdd: identity,
        eventChange: identity,
        eventRemove: identity,
        windowResize: identity,
        eventClick: identity,
        eventMouseEnter: identity,
        eventMouseLeave: identity,
        select: identity,
        unselect: identity,
        loading: identity,
        // internal
        _unmount: identity,
        _beforeprint: identity,
        _afterprint: identity,
        _noEventDrop: identity,
        _noEventResize: identity,
        _resize: identity,
        _scrollRequest: identity,
    };
    // calendar-specific options
    // -------------------------
    const CALENDAR_OPTION_REFINERS = {
        buttonText: identity,
        buttonHints: identity,
        views: identity,
        plugins: identity,
        initialEvents: identity,
        events: identity,
        eventSources: identity,
    };
    const COMPLEX_OPTION_COMPARATORS = {
        headerToolbar: isMaybeObjectsEqual,
        footerToolbar: isMaybeObjectsEqual,
        buttonText: isMaybeObjectsEqual,
        buttonHints: isMaybeObjectsEqual,
        buttonIcons: isMaybeObjectsEqual,
        dateIncrement: isMaybeObjectsEqual,
        plugins: isMaybeArraysEqual,
        events: isMaybeArraysEqual,
        eventSources: isMaybeArraysEqual,
        ['resources']: isMaybeArraysEqual,
    };
    function isMaybeObjectsEqual(a, b) {
        if (typeof a === 'object' && typeof b === 'object' && a && b) { // both non-null objects
            return isPropsEqual(a, b);
        }
        return a === b;
    }
    function isMaybeArraysEqual(a, b) {
        if (Array.isArray(a) && Array.isArray(b)) {
            return isArraysEqual(a, b);
        }
        return a === b;
    }
    // view-specific options
    // ---------------------
    const VIEW_OPTION_REFINERS = {
        type: String,
        component: identity,
        buttonText: String,
        buttonTextKey: String,
        dateProfileGeneratorClass: identity,
        usesMinMaxTime: Boolean,
        classNames: identity,
        content: identity,
        didMount: identity,
        willUnmount: identity,
    };
    // util funcs
    // ----------------------------------------------------------------------------------------------------
    function mergeRawOptions(optionSets) {
        return mergeProps(optionSets, COMPLEX_OPTION_COMPARATORS);
    }
    function refineProps(input, refiners) {
        let refined = {};
        let extra = {};
        for (let propName in refiners) {
            if (propName in input) {
                refined[propName] = refiners[propName](input[propName]);
            }
        }
        for (let propName in input) {
            if (!(propName in refiners)) {
                extra[propName] = input[propName];
            }
        }
        return { refined, extra };
    }
    function identity(raw) {
        return raw;
    }

    function createEventInstance(defId, range, forcedStartTzo, forcedEndTzo) {
        return {
            instanceId: guid(),
            defId,
            range,
            forcedStartTzo: forcedStartTzo == null ? null : forcedStartTzo,
            forcedEndTzo: forcedEndTzo == null ? null : forcedEndTzo,
        };
    }

    function parseRecurring(refined, defaultAllDay, dateEnv, recurringTypes) {
        for (let i = 0; i < recurringTypes.length; i += 1) {
            let parsed = recurringTypes[i].parse(refined, dateEnv);
            if (parsed) {
                let { allDay } = refined;
                if (allDay == null) {
                    allDay = defaultAllDay;
                    if (allDay == null) {
                        allDay = parsed.allDayGuess;
                        if (allDay == null) {
                            allDay = false;
                        }
                    }
                }
                return {
                    allDay,
                    duration: parsed.duration,
                    typeData: parsed.typeData,
                    typeId: i,
                };
            }
        }
        return null;
    }
    function expandRecurring(eventStore, framingRange, context) {
        let { dateEnv, pluginHooks, options } = context;
        let { defs, instances } = eventStore;
        // remove existing recurring instances
        // TODO: bad. always expand events as a second step
        instances = filterHash(instances, (instance) => !defs[instance.defId].recurringDef);
        for (let defId in defs) {
            let def = defs[defId];
            if (def.recurringDef) {
                let { duration } = def.recurringDef;
                if (!duration) {
                    duration = def.allDay ?
                        options.defaultAllDayEventDuration :
                        options.defaultTimedEventDuration;
                }
                let starts = expandRecurringRanges(def, duration, framingRange, dateEnv, pluginHooks.recurringTypes);
                for (let start of starts) {
                    let instance = createEventInstance(defId, {
                        start,
                        end: dateEnv.add(start, duration),
                    });
                    instances[instance.instanceId] = instance;
                }
            }
        }
        return { defs, instances };
    }
    /*
    Event MUST have a recurringDef
    */
    function expandRecurringRanges(eventDef, duration, framingRange, dateEnv, recurringTypes) {
        let typeDef = recurringTypes[eventDef.recurringDef.typeId];
        let markers = typeDef.expand(eventDef.recurringDef.typeData, {
            start: dateEnv.subtract(framingRange.start, duration),
            end: framingRange.end,
        }, dateEnv);
        // the recurrence plugins don't guarantee that all-day events are start-of-day, so we have to
        if (eventDef.allDay) {
            markers = markers.map(startOfDay);
        }
        return markers;
    }

    function parseEvents(rawEvents, eventSource, context, allowOpenRange, defIdMap, instanceIdMap) {
        let eventStore = createEmptyEventStore();
        let eventRefiners = buildEventRefiners(context);
        for (let rawEvent of rawEvents) {
            let tuple = parseEvent(rawEvent, eventSource, context, allowOpenRange, eventRefiners, defIdMap, instanceIdMap);
            if (tuple) {
                eventTupleToStore(tuple, eventStore);
            }
        }
        return eventStore;
    }
    function eventTupleToStore(tuple, eventStore = createEmptyEventStore()) {
        eventStore.defs[tuple.def.defId] = tuple.def;
        if (tuple.instance) {
            eventStore.instances[tuple.instance.instanceId] = tuple.instance;
        }
        return eventStore;
    }
    // retrieves events that have the same groupId as the instance specified by `instanceId`
    // or they are the same as the instance.
    // why might instanceId not be in the store? an event from another calendar?
    function getRelevantEvents(eventStore, instanceId) {
        let instance = eventStore.instances[instanceId];
        if (instance) {
            let def = eventStore.defs[instance.defId];
            // get events/instances with same group
            let newStore = filterEventStoreDefs(eventStore, (lookDef) => isEventDefsGrouped(def, lookDef));
            // add the original
            // TODO: wish we could use eventTupleToStore or something like it
            newStore.defs[def.defId] = def;
            newStore.instances[instance.instanceId] = instance;
            return newStore;
        }
        return createEmptyEventStore();
    }
    function isEventDefsGrouped(def0, def1) {
        return Boolean(def0.groupId && def0.groupId === def1.groupId);
    }
    function createEmptyEventStore() {
        return { defs: {}, instances: {} };
    }
    function mergeEventStores(store0, store1) {
        return {
            defs: Object.assign(Object.assign({}, store0.defs), store1.defs),
            instances: Object.assign(Object.assign({}, store0.instances), store1.instances),
        };
    }
    function filterEventStoreDefs(eventStore, filterFunc) {
        let defs = filterHash(eventStore.defs, filterFunc);
        let instances = filterHash(eventStore.instances, (instance) => (defs[instance.defId] // still exists?
        ));
        return { defs, instances };
    }
    function excludeSubEventStore(master, sub) {
        let { defs, instances } = master;
        let filteredDefs = {};
        let filteredInstances = {};
        for (let defId in defs) {
            if (!sub.defs[defId]) { // not explicitly excluded
                filteredDefs[defId] = defs[defId];
            }
        }
        for (let instanceId in instances) {
            if (!sub.instances[instanceId] && // not explicitly excluded
                filteredDefs[instances[instanceId].defId] // def wasn't filtered away
            ) {
                filteredInstances[instanceId] = instances[instanceId];
            }
        }
        return {
            defs: filteredDefs,
            instances: filteredInstances,
        };
    }

    function normalizeConstraint(input, context) {
        if (Array.isArray(input)) {
            return parseEvents(input, null, context, true); // allowOpenRange=true
        }
        if (typeof input === 'object' && input) { // non-null object
            return parseEvents([input], null, context, true); // allowOpenRange=true
        }
        if (input != null) {
            return String(input);
        }
        return null;
    }

    function parseClassNames(raw) {
        if (Array.isArray(raw)) {
            return raw;
        }
        if (typeof raw === 'string') {
            return raw.split(/\s+/);
        }
        return [];
    }

    // TODO: better called "EventSettings" or "EventConfig"
    // TODO: move this file into structs
    // TODO: separate constraint/overlap/allow, because selection uses only that, not other props
    const EVENT_UI_REFINERS = {
        display: String,
        editable: Boolean,
        startEditable: Boolean,
        durationEditable: Boolean,
        constraint: identity,
        overlap: identity,
        allow: identity,
        className: parseClassNames,
        classNames: parseClassNames,
        color: String,
        backgroundColor: String,
        borderColor: String,
        textColor: String,
    };
    const EMPTY_EVENT_UI = {
        display: null,
        startEditable: null,
        durationEditable: null,
        constraints: [],
        overlap: null,
        allows: [],
        backgroundColor: '',
        borderColor: '',
        textColor: '',
        classNames: [],
    };
    function createEventUi(refined, context) {
        let constraint = normalizeConstraint(refined.constraint, context);
        return {
            display: refined.display || null,
            startEditable: refined.startEditable != null ? refined.startEditable : refined.editable,
            durationEditable: refined.durationEditable != null ? refined.durationEditable : refined.editable,
            constraints: constraint != null ? [constraint] : [],
            overlap: refined.overlap != null ? refined.overlap : null,
            allows: refined.allow != null ? [refined.allow] : [],
            backgroundColor: refined.backgroundColor || refined.color || '',
            borderColor: refined.borderColor || refined.color || '',
            textColor: refined.textColor || '',
            classNames: (refined.className || []).concat(refined.classNames || []), // join singular and plural
        };
    }
    // TODO: prevent against problems with <2 args!
    function combineEventUis(uis) {
        return uis.reduce(combineTwoEventUis, EMPTY_EVENT_UI);
    }
    function combineTwoEventUis(item0, item1) {
        return {
            display: item1.display != null ? item1.display : item0.display,
            startEditable: item1.startEditable != null ? item1.startEditable : item0.startEditable,
            durationEditable: item1.durationEditable != null ? item1.durationEditable : item0.durationEditable,
            constraints: item0.constraints.concat(item1.constraints),
            overlap: typeof item1.overlap === 'boolean' ? item1.overlap : item0.overlap,
            allows: item0.allows.concat(item1.allows),
            backgroundColor: item1.backgroundColor || item0.backgroundColor,
            borderColor: item1.borderColor || item0.borderColor,
            textColor: item1.textColor || item0.textColor,
            classNames: item0.classNames.concat(item1.classNames),
        };
    }

    const EVENT_NON_DATE_REFINERS = {
        id: String,
        groupId: String,
        title: String,
        url: String,
        interactive: Boolean,
    };
    const EVENT_DATE_REFINERS = {
        start: identity,
        end: identity,
        date: identity,
        allDay: Boolean,
    };
    const EVENT_REFINERS = Object.assign(Object.assign(Object.assign({}, EVENT_NON_DATE_REFINERS), EVENT_DATE_REFINERS), { extendedProps: identity });
    function parseEvent(raw, eventSource, context, allowOpenRange, refiners = buildEventRefiners(context), defIdMap, instanceIdMap) {
        let { refined, extra } = refineEventDef(raw, context, refiners);
        let defaultAllDay = computeIsDefaultAllDay(eventSource, context);
        let recurringRes = parseRecurring(refined, defaultAllDay, context.dateEnv, context.pluginHooks.recurringTypes);
        if (recurringRes) {
            let def = parseEventDef(refined, extra, eventSource ? eventSource.sourceId : '', recurringRes.allDay, Boolean(recurringRes.duration), context, defIdMap);
            def.recurringDef = {
                typeId: recurringRes.typeId,
                typeData: recurringRes.typeData,
                duration: recurringRes.duration,
            };
            return { def, instance: null };
        }
        let singleRes = parseSingle(refined, defaultAllDay, context, allowOpenRange);
        if (singleRes) {
            let def = parseEventDef(refined, extra, eventSource ? eventSource.sourceId : '', singleRes.allDay, singleRes.hasEnd, context, defIdMap);
            let instance = createEventInstance(def.defId, singleRes.range, singleRes.forcedStartTzo, singleRes.forcedEndTzo);
            if (instanceIdMap && def.publicId && instanceIdMap[def.publicId]) {
                instance.instanceId = instanceIdMap[def.publicId];
            }
            return { def, instance };
        }
        return null;
    }
    function refineEventDef(raw, context, refiners = buildEventRefiners(context)) {
        return refineProps(raw, refiners);
    }
    function buildEventRefiners(context) {
        return Object.assign(Object.assign(Object.assign({}, EVENT_UI_REFINERS), EVENT_REFINERS), context.pluginHooks.eventRefiners);
    }
    /*
    Will NOT populate extendedProps with the leftover properties.
    Will NOT populate date-related props.
    */
    function parseEventDef(refined, extra, sourceId, allDay, hasEnd, context, defIdMap) {
        let def = {
            title: refined.title || '',
            groupId: refined.groupId || '',
            publicId: refined.id || '',
            url: refined.url || '',
            recurringDef: null,
            defId: ((defIdMap && refined.id) ? defIdMap[refined.id] : '') || guid(),
            sourceId,
            allDay,
            hasEnd,
            interactive: refined.interactive,
            ui: createEventUi(refined, context),
            extendedProps: Object.assign(Object.assign({}, (refined.extendedProps || {})), extra),
        };
        for (let memberAdder of context.pluginHooks.eventDefMemberAdders) {
            Object.assign(def, memberAdder(refined));
        }
        // help out EventImpl from having user modify props
        Object.freeze(def.ui.classNames);
        Object.freeze(def.extendedProps);
        return def;
    }
    function parseSingle(refined, defaultAllDay, context, allowOpenRange) {
        let { allDay } = refined;
        let startMeta;
        let startMarker = null;
        let hasEnd = false;
        let endMeta;
        let endMarker = null;
        let startInput = refined.start != null ? refined.start : refined.date;
        startMeta = context.dateEnv.createMarkerMeta(startInput);
        if (startMeta) {
            startMarker = startMeta.marker;
        }
        else if (!allowOpenRange) {
            return null;
        }
        if (refined.end != null) {
            endMeta = context.dateEnv.createMarkerMeta(refined.end);
        }
        if (allDay == null) {
            if (defaultAllDay != null) {
                allDay = defaultAllDay;
            }
            else {
                // fall back to the date props LAST
                allDay = (!startMeta || startMeta.isTimeUnspecified) &&
                    (!endMeta || endMeta.isTimeUnspecified);
            }
        }
        if (allDay && startMarker) {
            startMarker = startOfDay(startMarker);
        }
        if (endMeta) {
            endMarker = endMeta.marker;
            if (allDay) {
                endMarker = startOfDay(endMarker);
            }
            if (startMarker && endMarker <= startMarker) {
                endMarker = null;
            }
        }
        if (endMarker) {
            hasEnd = true;
        }
        else if (!allowOpenRange) {
            hasEnd = context.options.forceEventDuration || false;
            endMarker = context.dateEnv.add(startMarker, allDay ?
                context.options.defaultAllDayEventDuration :
                context.options.defaultTimedEventDuration);
        }
        return {
            allDay,
            hasEnd,
            range: { start: startMarker, end: endMarker },
            forcedStartTzo: startMeta ? startMeta.forcedTzo : null,
            forcedEndTzo: endMeta ? endMeta.forcedTzo : null,
        };
    }
    function computeIsDefaultAllDay(eventSource, context) {
        let res = null;
        if (eventSource) {
            res = eventSource.defaultAllDay;
        }
        if (res == null) {
            res = context.options.defaultAllDay;
        }
        return res;
    }

    const DEF_DEFAULTS = {
        startTime: '09:00',
        endTime: '17:00',
        daysOfWeek: [1, 2, 3, 4, 5],
        display: 'inverse-background',
        classNames: 'fc-non-business',
        groupId: '_businessHours', // so multiple defs get grouped
    };
    /*
    TODO: pass around as EventDefHash!!!
    */
    function parseBusinessHours(input, context) {
        return parseEvents(refineInputs(input), null, context);
    }
    function refineInputs(input) {
        let rawDefs;
        if (input === true) {
            rawDefs = [{}]; // will get DEF_DEFAULTS verbatim
        }
        else if (Array.isArray(input)) {
            // if specifying an array, every sub-definition NEEDS a day-of-week
            rawDefs = input.filter((rawDef) => rawDef.daysOfWeek);
        }
        else if (typeof input === 'object' && input) { // non-null object
            rawDefs = [input];
        }
        else { // is probably false
            rawDefs = [];
        }
        rawDefs = rawDefs.map((rawDef) => (Object.assign(Object.assign({}, DEF_DEFAULTS), rawDef)));
        return rawDefs;
    }

    /* Date stuff that doesn't belong in datelib core
    ----------------------------------------------------------------------------------------------------------------------*/
    // given a timed range, computes an all-day range that has the same exact duration,
    // but whose start time is aligned with the start of the day.
    function computeAlignedDayRange(timedRange) {
        let dayCnt = Math.floor(diffDays(timedRange.start, timedRange.end)) || 1;
        let start = startOfDay(timedRange.start);
        let end = addDays(start, dayCnt);
        return { start, end };
    }
    // given a timed range, computes an all-day range based on how for the end date bleeds into the next day
    // TODO: give nextDayThreshold a default arg
    function computeVisibleDayRange(timedRange, nextDayThreshold = createDuration(0)) {
        let startDay = null;
        let endDay = null;
        if (timedRange.end) {
            endDay = startOfDay(timedRange.end);
            let endTimeMS = timedRange.end.valueOf() - endDay.valueOf(); // # of milliseconds into `endDay`
            // If the end time is actually inclusively part of the next day and is equal to or
            // beyond the next day threshold, adjust the end to be the exclusive end of `endDay`.
            // Otherwise, leaving it as inclusive will cause it to exclude `endDay`.
            if (endTimeMS && endTimeMS >= asRoughMs(nextDayThreshold)) {
                endDay = addDays(endDay, 1);
            }
        }
        if (timedRange.start) {
            startDay = startOfDay(timedRange.start); // the beginning of the day the range starts
            // If end is within `startDay` but not past nextDayThreshold, assign the default duration of one day.
            if (endDay && endDay <= startDay) {
                endDay = addDays(startDay, 1);
            }
        }
        return { start: startDay, end: endDay };
    }
    // spans from one day into another?
    function isMultiDayRange(range) {
        let visibleRange = computeVisibleDayRange(range);
        return diffDays(visibleRange.start, visibleRange.end) > 1;
    }
    function diffDates(date0, date1, dateEnv, largeUnit) {
        if (largeUnit === 'year') {
            return createDuration(dateEnv.diffWholeYears(date0, date1), 'year');
        }
        if (largeUnit === 'month') {
            return createDuration(dateEnv.diffWholeMonths(date0, date1), 'month');
        }
        return diffDayAndTime(date0, date1); // returns a duration
    }

    function pointInsideRect(point, rect) {
        return point.left >= rect.left &&
            point.left < rect.right &&
            point.top >= rect.top &&
            point.top < rect.bottom;
    }
    // Returns a new rectangle that is the intersection of the two rectangles. If they don't intersect, returns false
    function intersectRects(rect1, rect2) {
        let res = {
            left: Math.max(rect1.left, rect2.left),
            right: Math.min(rect1.right, rect2.right),
            top: Math.max(rect1.top, rect2.top),
            bottom: Math.min(rect1.bottom, rect2.bottom),
        };
        if (res.left < res.right && res.top < res.bottom) {
            return res;
        }
        return false;
    }
    function translateRect(rect, deltaX, deltaY) {
        return {
            left: rect.left + deltaX,
            right: rect.right + deltaX,
            top: rect.top + deltaY,
            bottom: rect.bottom + deltaY,
        };
    }
    // Returns a new point that will have been moved to reside within the given rectangle
    function constrainPoint(point, rect) {
        return {
            left: Math.min(Math.max(point.left, rect.left), rect.right),
            top: Math.min(Math.max(point.top, rect.top), rect.bottom),
        };
    }
    // Returns a point that is the center of the given rectangle
    function getRectCenter(rect) {
        return {
            left: (rect.left + rect.right) / 2,
            top: (rect.top + rect.bottom) / 2,
        };
    }
    // Subtracts point2's coordinates from point1's coordinates, returning a delta
    function diffPoints(point1, point2) {
        return {
            left: point1.left - point2.left,
            top: point1.top - point2.top,
        };
    }

    let canVGrowWithinCell;
    function getCanVGrowWithinCell() {
        if (canVGrowWithinCell == null) {
            canVGrowWithinCell = computeCanVGrowWithinCell();
        }
        return canVGrowWithinCell;
    }
    function computeCanVGrowWithinCell() {
        // for SSR, because this function is call immediately at top-level
        // TODO: just make this logic execute top-level, immediately, instead of doing lazily
        if (typeof document === 'undefined') {
            return true;
        }
        let el = document.createElement('div');
        el.style.position = 'absolute';
        el.style.top = '0px';
        el.style.left = '0px';
        el.innerHTML = '<table><tr><td><div></div></td></tr></table>';
        el.querySelector('table').style.height = '100px';
        el.querySelector('div').style.height = '100%';
        document.body.appendChild(el);
        let div = el.querySelector('div');
        let possible = div.offsetHeight > 0;
        document.body.removeChild(el);
        return possible;
    }

    const EMPTY_EVENT_STORE = createEmptyEventStore(); // for purecomponents. TODO: keep elsewhere
    class Splitter {
        constructor() {
            this.getKeysForEventDefs = memoize(this._getKeysForEventDefs);
            this.splitDateSelection = memoize(this._splitDateSpan);
            this.splitEventStore = memoize(this._splitEventStore);
            this.splitIndividualUi = memoize(this._splitIndividualUi);
            this.splitEventDrag = memoize(this._splitInteraction);
            this.splitEventResize = memoize(this._splitInteraction);
            this.eventUiBuilders = {}; // TODO: typescript protection
        }
        splitProps(props) {
            let keyInfos = this.getKeyInfo(props);
            let defKeys = this.getKeysForEventDefs(props.eventStore);
            let dateSelections = this.splitDateSelection(props.dateSelection);
            let individualUi = this.splitIndividualUi(props.eventUiBases, defKeys); // the individual *bases*
            let eventStores = this.splitEventStore(props.eventStore, defKeys);
            let eventDrags = this.splitEventDrag(props.eventDrag);
            let eventResizes = this.splitEventResize(props.eventResize);
            let splitProps = {};
            this.eventUiBuilders = mapHash(keyInfos, (info, key) => this.eventUiBuilders[key] || memoize(buildEventUiForKey));
            for (let key in keyInfos) {
                let keyInfo = keyInfos[key];
                let eventStore = eventStores[key] || EMPTY_EVENT_STORE;
                let buildEventUi = this.eventUiBuilders[key];
                splitProps[key] = {
                    businessHours: keyInfo.businessHours || props.businessHours,
                    dateSelection: dateSelections[key] || null,
                    eventStore,
                    eventUiBases: buildEventUi(props.eventUiBases[''], keyInfo.ui, individualUi[key]),
                    eventSelection: eventStore.instances[props.eventSelection] ? props.eventSelection : '',
                    eventDrag: eventDrags[key] || null,
                    eventResize: eventResizes[key] || null,
                };
            }
            return splitProps;
        }
        _splitDateSpan(dateSpan) {
            let dateSpans = {};
            if (dateSpan) {
                let keys = this.getKeysForDateSpan(dateSpan);
                for (let key of keys) {
                    dateSpans[key] = dateSpan;
                }
            }
            return dateSpans;
        }
        _getKeysForEventDefs(eventStore) {
            return mapHash(eventStore.defs, (eventDef) => this.getKeysForEventDef(eventDef));
        }
        _splitEventStore(eventStore, defKeys) {
            let { defs, instances } = eventStore;
            let splitStores = {};
            for (let defId in defs) {
                for (let key of defKeys[defId]) {
                    if (!splitStores[key]) {
                        splitStores[key] = createEmptyEventStore();
                    }
                    splitStores[key].defs[defId] = defs[defId];
                }
            }
            for (let instanceId in instances) {
                let instance = instances[instanceId];
                for (let key of defKeys[instance.defId]) {
                    if (splitStores[key]) { // must have already been created
                        splitStores[key].instances[instanceId] = instance;
                    }
                }
            }
            return splitStores;
        }
        _splitIndividualUi(eventUiBases, defKeys) {
            let splitHashes = {};
            for (let defId in eventUiBases) {
                if (defId) { // not the '' key
                    for (let key of defKeys[defId]) {
                        if (!splitHashes[key]) {
                            splitHashes[key] = {};
                        }
                        splitHashes[key][defId] = eventUiBases[defId];
                    }
                }
            }
            return splitHashes;
        }
        _splitInteraction(interaction) {
            let splitStates = {};
            if (interaction) {
                let affectedStores = this._splitEventStore(interaction.affectedEvents, this._getKeysForEventDefs(interaction.affectedEvents));
                // can't rely on defKeys because event data is mutated
                let mutatedKeysByDefId = this._getKeysForEventDefs(interaction.mutatedEvents);
                let mutatedStores = this._splitEventStore(interaction.mutatedEvents, mutatedKeysByDefId);
                let populate = (key) => {
                    if (!splitStates[key]) {
                        splitStates[key] = {
                            affectedEvents: affectedStores[key] || EMPTY_EVENT_STORE,
                            mutatedEvents: mutatedStores[key] || EMPTY_EVENT_STORE,
                            isEvent: interaction.isEvent,
                        };
                    }
                };
                for (let key in affectedStores) {
                    populate(key);
                }
                for (let key in mutatedStores) {
                    populate(key);
                }
            }
            return splitStates;
        }
    }
    function buildEventUiForKey(allUi, eventUiForKey, individualUi) {
        let baseParts = [];
        if (allUi) {
            baseParts.push(allUi);
        }
        if (eventUiForKey) {
            baseParts.push(eventUiForKey);
        }
        let stuff = {
            '': combineEventUis(baseParts),
        };
        if (individualUi) {
            Object.assign(stuff, individualUi);
        }
        return stuff;
    }

    function parseRange(input, dateEnv) {
        let start = null;
        let end = null;
        if (input.start) {
            start = dateEnv.createMarker(input.start);
        }
        if (input.end) {
            end = dateEnv.createMarker(input.end);
        }
        if (!start && !end) {
            return null;
        }
        if (start && end && end < start) {
            return null;
        }
        return { start, end };
    }
    // SIDE-EFFECT: will mutate ranges.
    // Will return a new array result.
    function invertRanges(ranges, constraintRange) {
        let invertedRanges = [];
        let { start } = constraintRange; // the end of the previous range. the start of the new range
        let i;
        let dateRange;
        // ranges need to be in order. required for our date-walking algorithm
        ranges.sort(compareRanges);
        for (i = 0; i < ranges.length; i += 1) {
            dateRange = ranges[i];
            // add the span of time before the event (if there is any)
            if (dateRange.start > start) { // compare millisecond time (skip any ambig logic)
                invertedRanges.push({ start, end: dateRange.start });
            }
            if (dateRange.end > start) {
                start = dateRange.end;
            }
        }
        // add the span of time after the last event (if there is any)
        if (start < constraintRange.end) { // compare millisecond time (skip any ambig logic)
            invertedRanges.push({ start, end: constraintRange.end });
        }
        return invertedRanges;
    }
    function compareRanges(range0, range1) {
        return range0.start.valueOf() - range1.start.valueOf(); // earlier ranges go first
    }
    function intersectRanges(range0, range1) {
        let { start, end } = range0;
        let newRange = null;
        if (range1.start !== null) {
            if (start === null) {
                start = range1.start;
            }
            else {
                start = new Date(Math.max(start.valueOf(), range1.start.valueOf()));
            }
        }
        if (range1.end != null) {
            if (end === null) {
                end = range1.end;
            }
            else {
                end = new Date(Math.min(end.valueOf(), range1.end.valueOf()));
            }
        }
        if (start === null || end === null || start < end) {
            newRange = { start, end };
        }
        return newRange;
    }
    function rangesEqual(range0, range1) {
        return (range0.start === null ? null : range0.start.valueOf()) === (range1.start === null ? null : range1.start.valueOf()) &&
            (range0.end === null ? null : range0.end.valueOf()) === (range1.end === null ? null : range1.end.valueOf());
    }
    function rangesIntersect(range0, range1) {
        return (range0.end === null || range1.start === null || range0.end > range1.start) &&
            (range0.start === null || range1.end === null || range0.start < range1.end);
    }
    function rangeContainsRange(outerRange, innerRange) {
        return (outerRange.start === null || (innerRange.start !== null && innerRange.start >= outerRange.start)) &&
            (outerRange.end === null || (innerRange.end !== null && innerRange.end <= outerRange.end));
    }
    function rangeContainsMarker(range, date) {
        return (range.start === null || date >= range.start) &&
            (range.end === null || date < range.end);
    }
    // If the given date is not within the given range, move it inside.
    // (If it's past the end, make it one millisecond before the end).
    function constrainMarkerToRange(date, range) {
        if (range.start != null && date < range.start) {
            return range.start;
        }
        if (range.end != null && date >= range.end) {
            return new Date(range.end.valueOf() - 1);
        }
        return date;
    }

    function getDateMeta(date, todayRange, nowDate, dateProfile) {
        return {
            dow: date.getUTCDay(),
            isDisabled: Boolean(dateProfile && (!dateProfile.activeRange || !rangeContainsMarker(dateProfile.activeRange, date))),
            isOther: Boolean(dateProfile && !rangeContainsMarker(dateProfile.currentRange, date)),
            isToday: Boolean(todayRange && rangeContainsMarker(todayRange, date)),
            isPast: Boolean(nowDate ? (date < nowDate) : todayRange ? (date < todayRange.start) : false),
            isFuture: Boolean(nowDate ? (date > nowDate) : todayRange ? (date >= todayRange.end) : false),
        };
    }
    function getDayClassNames(meta, theme) {
        let classNames = [
            'fc-day',
            `fc-day-${DAY_IDS[meta.dow]}`,
        ];
        if (meta.isDisabled) {
            classNames.push('fc-day-disabled');
        }
        else {
            if (meta.isToday) {
                classNames.push('fc-day-today');
                classNames.push(theme.getClass('today'));
            }
            if (meta.isPast) {
                classNames.push('fc-day-past');
            }
            if (meta.isFuture) {
                classNames.push('fc-day-future');
            }
            if (meta.isOther) {
                classNames.push('fc-day-other');
            }
        }
        return classNames;
    }
    function getSlotClassNames(meta, theme) {
        let classNames = [
            'fc-slot',
            `fc-slot-${DAY_IDS[meta.dow]}`,
        ];
        if (meta.isDisabled) {
            classNames.push('fc-slot-disabled');
        }
        else {
            if (meta.isToday) {
                classNames.push('fc-slot-today');
                classNames.push(theme.getClass('today'));
            }
            if (meta.isPast) {
                classNames.push('fc-slot-past');
            }
            if (meta.isFuture) {
                classNames.push('fc-slot-future');
            }
        }
        return classNames;
    }

    const DAY_FORMAT = createFormatter({ year: 'numeric', month: 'long', day: 'numeric' });
    const WEEK_FORMAT = createFormatter({ week: 'long' });
    function buildNavLinkAttrs(context, dateMarker, viewType = 'day', isTabbable = true) {
        const { dateEnv, options, calendarApi } = context;
        let dateStr = dateEnv.format(dateMarker, viewType === 'week' ? WEEK_FORMAT : DAY_FORMAT);
        if (options.navLinks) {
            let zonedDate = dateEnv.toDate(dateMarker);
            const handleInteraction = (ev) => {
                let customAction = viewType === 'day' ? options.navLinkDayClick :
                    viewType === 'week' ? options.navLinkWeekClick : null;
                if (typeof customAction === 'function') {
                    customAction.call(calendarApi, dateEnv.toDate(dateMarker), ev);
                }
                else {
                    if (typeof customAction === 'string') {
                        viewType = customAction;
                    }
                    calendarApi.zoomTo(dateMarker, viewType);
                }
            };
            return Object.assign({ title: formatWithOrdinals(options.navLinkHint, [dateStr, zonedDate], dateStr), 'data-navlink': '' }, (isTabbable
                ? createAriaClickAttrs(handleInteraction)
                : { onClick: handleInteraction }));
        }
        return { 'aria-label': dateStr };
    }

    let _isRtlScrollbarOnLeft = null;
    function getIsRtlScrollbarOnLeft() {
        if (_isRtlScrollbarOnLeft === null) {
            _isRtlScrollbarOnLeft = computeIsRtlScrollbarOnLeft();
        }
        return _isRtlScrollbarOnLeft;
    }
    function computeIsRtlScrollbarOnLeft() {
        let outerEl = document.createElement('div');
        applyStyle(outerEl, {
            position: 'absolute',
            top: -1000,
            left: 0,
            border: 0,
            padding: 0,
            overflow: 'scroll',
            direction: 'rtl',
        });
        outerEl.innerHTML = '<div></div>';
        document.body.appendChild(outerEl);
        let innerEl = outerEl.firstChild;
        let res = innerEl.getBoundingClientRect().left > outerEl.getBoundingClientRect().left;
        removeElement(outerEl);
        return res;
    }

    let _scrollbarWidths;
    function getScrollbarWidths() {
        if (!_scrollbarWidths) {
            _scrollbarWidths = computeScrollbarWidths();
        }
        return _scrollbarWidths;
    }
    function computeScrollbarWidths() {
        let el = document.createElement('div');
        el.style.overflow = 'scroll';
        el.style.position = 'absolute';
        el.style.top = '-9999px';
        el.style.left = '-9999px';
        document.body.appendChild(el);
        let res = computeScrollbarWidthsForEl(el);
        document.body.removeChild(el);
        return res;
    }
    // WARNING: will include border
    function computeScrollbarWidthsForEl(el) {
        return {
            x: el.offsetHeight - el.clientHeight,
            y: el.offsetWidth - el.clientWidth,
        };
    }

    function computeEdges(el, getPadding = false) {
        let computedStyle = window.getComputedStyle(el);
        let borderLeft = parseInt(computedStyle.borderLeftWidth, 10) || 0;
        let borderRight = parseInt(computedStyle.borderRightWidth, 10) || 0;
        let borderTop = parseInt(computedStyle.borderTopWidth, 10) || 0;
        let borderBottom = parseInt(computedStyle.borderBottomWidth, 10) || 0;
        let badScrollbarWidths = computeScrollbarWidthsForEl(el); // includes border!
        let scrollbarLeftRight = badScrollbarWidths.y - borderLeft - borderRight;
        let scrollbarBottom = badScrollbarWidths.x - borderTop - borderBottom;
        let res = {
            borderLeft,
            borderRight,
            borderTop,
            borderBottom,
            scrollbarBottom,
            scrollbarLeft: 0,
            scrollbarRight: 0,
        };
        if (getIsRtlScrollbarOnLeft() && computedStyle.direction === 'rtl') { // is the scrollbar on the left side?
            res.scrollbarLeft = scrollbarLeftRight;
        }
        else {
            res.scrollbarRight = scrollbarLeftRight;
        }
        if (getPadding) {
            res.paddingLeft = parseInt(computedStyle.paddingLeft, 10) || 0;
            res.paddingRight = parseInt(computedStyle.paddingRight, 10) || 0;
            res.paddingTop = parseInt(computedStyle.paddingTop, 10) || 0;
            res.paddingBottom = parseInt(computedStyle.paddingBottom, 10) || 0;
        }
        return res;
    }
    function computeInnerRect(el, goWithinPadding = false, doFromWindowViewport) {
        let outerRect = doFromWindowViewport ? el.getBoundingClientRect() : computeRect(el);
        let edges = computeEdges(el, goWithinPadding);
        let res = {
            left: outerRect.left + edges.borderLeft + edges.scrollbarLeft,
            right: outerRect.right - edges.borderRight - edges.scrollbarRight,
            top: outerRect.top + edges.borderTop,
            bottom: outerRect.bottom - edges.borderBottom - edges.scrollbarBottom,
        };
        if (goWithinPadding) {
            res.left += edges.paddingLeft;
            res.right -= edges.paddingRight;
            res.top += edges.paddingTop;
            res.bottom -= edges.paddingBottom;
        }
        return res;
    }
    function computeRect(el) {
        let rect = el.getBoundingClientRect();
        return {
            left: rect.left + window.scrollX,
            top: rect.top + window.scrollY,
            right: rect.right + window.scrollX,
            bottom: rect.bottom + window.scrollY,
        };
    }
    function computeClippedClientRect(el) {
        let clippingParents = getClippingParents(el);
        let rect = el.getBoundingClientRect();
        for (let clippingParent of clippingParents) {
            let intersection = intersectRects(rect, clippingParent.getBoundingClientRect());
            if (intersection) {
                rect = intersection;
            }
            else {
                return null;
            }
        }
        return rect;
    }
    // does not return window
    function getClippingParents(el) {
        let parents = [];
        while (el instanceof HTMLElement) { // will stop when gets to document or null
            let computedStyle = window.getComputedStyle(el);
            if (computedStyle.position === 'fixed') {
                break;
            }
            if ((/(auto|scroll)/).test(computedStyle.overflow + computedStyle.overflowY + computedStyle.overflowX)) {
                parents.push(el);
            }
            el = el.parentNode;
        }
        return parents;
    }

    /*
    given a function that resolves a result asynchronously.
    the function can either call passed-in success and failure callbacks,
    or it can return a promise.
    if you need to pass additional params to func, bind them first.
    */
    function unpromisify(func, normalizedSuccessCallback, normalizedFailureCallback) {
        // guard against success/failure callbacks being called more than once
        // and guard against a promise AND callback being used together.
        let isResolved = false;
        let wrappedSuccess = function (res) {
            if (!isResolved) {
                isResolved = true;
                normalizedSuccessCallback(res);
            }
        };
        let wrappedFailure = function (error) {
            if (!isResolved) {
                isResolved = true;
                normalizedFailureCallback(error);
            }
        };
        let res = func(wrappedSuccess, wrappedFailure);
        if (res && typeof res.then === 'function') {
            res.then(wrappedSuccess, wrappedFailure);
        }
    }

    class Emitter {
        constructor() {
            this.handlers = {};
            this.thisContext = null;
        }
        setThisContext(thisContext) {
            this.thisContext = thisContext;
        }
        setOptions(options) {
            this.options = options;
        }
        on(type, handler) {
            addToHash(this.handlers, type, handler);
        }
        off(type, handler) {
            removeFromHash(this.handlers, type, handler);
        }
        trigger(type, ...args) {
            let attachedHandlers = this.handlers[type] || [];
            let optionHandler = this.options && this.options[type];
            let handlers = [].concat(optionHandler || [], attachedHandlers);
            for (let handler of handlers) {
                handler.apply(this.thisContext, args);
            }
        }
        hasHandlers(type) {
            return Boolean((this.handlers[type] && this.handlers[type].length) ||
                (this.options && this.options[type]));
        }
    }
    function addToHash(hash, type, handler) {
        (hash[type] || (hash[type] = []))
            .push(handler);
    }
    function removeFromHash(hash, type, handler) {
        if (handler) {
            if (hash[type]) {
                hash[type] = hash[type].filter((func) => func !== handler);
            }
        }
        else {
            delete hash[type]; // remove all handler funcs for this type
        }
    }

    /*
    Records offset information for a set of elements, relative to an origin element.
    Can record the left/right OR the top/bottom OR both.
    Provides methods for querying the cache by position.
    */
    class PositionCache {
        constructor(originEl, els, isHorizontal, isVertical) {
            this.els = els;
            let originClientRect = this.originClientRect = originEl.getBoundingClientRect(); // relative to viewport top-left
            if (isHorizontal) {
                this.buildElHorizontals(originClientRect.left);
            }
            if (isVertical) {
                this.buildElVerticals(originClientRect.top);
            }
        }
        // Populates the left/right internal coordinate arrays
        buildElHorizontals(originClientLeft) {
            let lefts = [];
            let rights = [];
            for (let el of this.els) {
                let rect = el.getBoundingClientRect();
                lefts.push(rect.left - originClientLeft);
                rights.push(rect.right - originClientLeft);
            }
            this.lefts = lefts;
            this.rights = rights;
        }
        // Populates the top/bottom internal coordinate arrays
        buildElVerticals(originClientTop) {
            let tops = [];
            let bottoms = [];
            for (let el of this.els) {
                let rect = el.getBoundingClientRect();
                tops.push(rect.top - originClientTop);
                bottoms.push(rect.bottom - originClientTop);
            }
            this.tops = tops;
            this.bottoms = bottoms;
        }
        // Given a left offset (from document left), returns the index of the el that it horizontally intersects.
        // If no intersection is made, returns undefined.
        leftToIndex(leftPosition) {
            let { lefts, rights } = this;
            let len = lefts.length;
            let i;
            for (i = 0; i < len; i += 1) {
                if (leftPosition >= lefts[i] && leftPosition < rights[i]) {
                    return i;
                }
            }
            return undefined; // TODO: better
        }
        // Given a top offset (from document top), returns the index of the el that it vertically intersects.
        // If no intersection is made, returns undefined.
        topToIndex(topPosition) {
            let { tops, bottoms } = this;
            let len = tops.length;
            let i;
            for (i = 0; i < len; i += 1) {
                if (topPosition >= tops[i] && topPosition < bottoms[i]) {
                    return i;
                }
            }
            return undefined; // TODO: better
        }
        // Gets the width of the element at the given index
        getWidth(leftIndex) {
            return this.rights[leftIndex] - this.lefts[leftIndex];
        }
        // Gets the height of the element at the given index
        getHeight(topIndex) {
            return this.bottoms[topIndex] - this.tops[topIndex];
        }
        similarTo(otherCache) {
            return similarNumArrays(this.tops || [], otherCache.tops || []) &&
                similarNumArrays(this.bottoms || [], otherCache.bottoms || []) &&
                similarNumArrays(this.lefts || [], otherCache.lefts || []) &&
                similarNumArrays(this.rights || [], otherCache.rights || []);
        }
    }
    function similarNumArrays(a, b) {
        const len = a.length;
        if (len !== b.length) {
            return false;
        }
        for (let i = 0; i < len; i++) {
            if (Math.round(a[i]) !== Math.round(b[i])) {
                return false;
            }
        }
        return true;
    }

    /* eslint max-classes-per-file: "off" */
    /*
    An object for getting/setting scroll-related information for an element.
    Internally, this is done very differently for window versus DOM element,
    so this object serves as a common interface.
    */
    class ScrollController {
        getMaxScrollTop() {
            return this.getScrollHeight() - this.getClientHeight();
        }
        getMaxScrollLeft() {
            return this.getScrollWidth() - this.getClientWidth();
        }
        canScrollVertically() {
            return this.getMaxScrollTop() > 0;
        }
        canScrollHorizontally() {
            return this.getMaxScrollLeft() > 0;
        }
        canScrollUp() {
            return this.getScrollTop() > 0;
        }
        canScrollDown() {
            return this.getScrollTop() < this.getMaxScrollTop();
        }
        canScrollLeft() {
            return this.getScrollLeft() > 0;
        }
        canScrollRight() {
            return this.getScrollLeft() < this.getMaxScrollLeft();
        }
    }
    class ElementScrollController extends ScrollController {
        constructor(el) {
            super();
            this.el = el;
        }
        getScrollTop() {
            return this.el.scrollTop;
        }
        getScrollLeft() {
            return this.el.scrollLeft;
        }
        setScrollTop(top) {
            this.el.scrollTop = top;
        }
        setScrollLeft(left) {
            this.el.scrollLeft = left;
        }
        getScrollWidth() {
            return this.el.scrollWidth;
        }
        getScrollHeight() {
            return this.el.scrollHeight;
        }
        getClientHeight() {
            return this.el.clientHeight;
        }
        getClientWidth() {
            return this.el.clientWidth;
        }
    }
    class WindowScrollController extends ScrollController {
        getScrollTop() {
            return window.scrollY;
        }
        getScrollLeft() {
            return window.scrollX;
        }
        setScrollTop(n) {
            window.scroll(window.scrollX, n);
        }
        setScrollLeft(n) {
            window.scroll(n, window.scrollY);
        }
        getScrollWidth() {
            return document.documentElement.scrollWidth;
        }
        getScrollHeight() {
            return document.documentElement.scrollHeight;
        }
        getClientHeight() {
            return document.documentElement.clientHeight;
        }
        getClientWidth() {
            return document.documentElement.clientWidth;
        }
    }

    class Theme {
        constructor(calendarOptions) {
            if (this.iconOverrideOption) {
                this.setIconOverride(calendarOptions[this.iconOverrideOption]);
            }
        }
        setIconOverride(iconOverrideHash) {
            let iconClassesCopy;
            let buttonName;
            if (typeof iconOverrideHash === 'object' && iconOverrideHash) { // non-null object
                iconClassesCopy = Object.assign({}, this.iconClasses);
                for (buttonName in iconOverrideHash) {
                    iconClassesCopy[buttonName] = this.applyIconOverridePrefix(iconOverrideHash[buttonName]);
                }
                this.iconClasses = iconClassesCopy;
            }
            else if (iconOverrideHash === false) {
                this.iconClasses = {};
            }
        }
        applyIconOverridePrefix(className) {
            let prefix = this.iconOverridePrefix;
            if (prefix && className.indexOf(prefix) !== 0) { // if not already present
                className = prefix + className;
            }
            return className;
        }
        getClass(key) {
            return this.classes[key] || '';
        }
        getIconClass(buttonName, isRtl) {
            let className;
            if (isRtl && this.rtlIconClasses) {
                className = this.rtlIconClasses[buttonName] || this.iconClasses[buttonName];
            }
            else {
                className = this.iconClasses[buttonName];
            }
            if (className) {
                return `${this.baseIconClass} ${className}`;
            }
            return '';
        }
        getCustomButtonIconClass(customButtonProps) {
            let className;
            if (this.iconOverrideCustomButtonOption) {
                className = customButtonProps[this.iconOverrideCustomButtonOption];
                if (className) {
                    return `${this.baseIconClass} ${this.applyIconOverridePrefix(className)}`;
                }
            }
            return '';
        }
    }
    Theme.prototype.classes = {};
    Theme.prototype.iconClasses = {};
    Theme.prototype.baseIconClass = '';
    Theme.prototype.iconOverridePrefix = '';

    var n,l$1,u$1,i$1,t,r$1,o,f$1,e$1,c$1={},s=[],a$1=/acit|ex(?:s|g|n|p|$)|rph|grid|ows|mnc|ntw|ine[ch]|zoo|^ord|itera/i;function h(n,l){for(var u in l)n[u]=l[u];return n}function v$1(n){var l=n.parentNode;l&&l.removeChild(n);}function y(l,u,i){var t,r,o,f={};for(o in u)"key"==o?t=u[o]:"ref"==o?r=u[o]:f[o]=u[o];if(arguments.length>2&&(f.children=arguments.length>3?n.call(arguments,2):i),"function"==typeof l&&null!=l.defaultProps)for(o in l.defaultProps)void 0===f[o]&&(f[o]=l.defaultProps[o]);return p(l,f,t,r,null)}function p(n,i,t,r,o){var f={type:n,props:i,key:t,ref:r,__k:null,__:null,__b:0,__e:null,__d:void 0,__c:null,__h:null,constructor:void 0,__v:null==o?++u$1:o};return null==o&&null!=l$1.vnode&&l$1.vnode(f),f}function d(){return {current:null}}function _(n){return n.children}function k$1(n,l,u,i,t){var r;for(r in u)"children"===r||"key"===r||r in l||g$2(n,r,null,u[r],i);for(r in l)t&&"function"!=typeof l[r]||"children"===r||"key"===r||"value"===r||"checked"===r||u[r]===l[r]||g$2(n,r,l[r],u[r],i);}function b$1(n,l,u){"-"===l[0]?n.setProperty(l,null==u?"":u):n[l]=null==u?"":"number"!=typeof u||a$1.test(l)?u:u+"px";}function g$2(n,l,u,i,t){var r;n:if("style"===l)if("string"==typeof u)n.style.cssText=u;else {if("string"==typeof i&&(n.style.cssText=i=""),i)for(l in i)u&&l in u||b$1(n.style,l,"");if(u)for(l in u)i&&u[l]===i[l]||b$1(n.style,l,u[l]);}else if("o"===l[0]&&"n"===l[1])r=l!==(l=l.replace(/Capture$/,"")),l=l.toLowerCase()in n?l.toLowerCase().slice(2):l.slice(2),n.l||(n.l={}),n.l[l+r]=u,u?i||n.addEventListener(l,r?w$2:m$1,r):n.removeEventListener(l,r?w$2:m$1,r);else if("dangerouslySetInnerHTML"!==l){if(t)l=l.replace(/xlink(H|:h)/,"h").replace(/sName$/,"s");else if("width"!==l&&"height"!==l&&"href"!==l&&"list"!==l&&"form"!==l&&"tabIndex"!==l&&"download"!==l&&l in n)try{n[l]=null==u?"":u;break n}catch(n){}"function"==typeof u||(null==u||!1===u&&-1==l.indexOf("-")?n.removeAttribute(l):n.setAttribute(l,u));}}function m$1(n){t=!0;try{return this.l[n.type+!1](l$1.event?l$1.event(n):n)}finally{t=!1;}}function w$2(n){t=!0;try{return this.l[n.type+!0](l$1.event?l$1.event(n):n)}finally{t=!1;}}function x$1(n,l){this.props=n,this.context=l;}function A(n,l){if(null==l)return n.__?A(n.__,n.__.__k.indexOf(n)+1):null;for(var u;l<n.__k.length;l++)if(null!=(u=n.__k[l])&&null!=u.__e)return u.__e;return "function"==typeof n.type?A(n):null}function P$1(n){var l,u;if(null!=(n=n.__)&&null!=n.__c){for(n.__e=n.__c.base=null,l=0;l<n.__k.length;l++)if(null!=(u=n.__k[l])&&null!=u.__e){n.__e=n.__c.base=u.__e;break}return P$1(n)}}function C$1(n){t?setTimeout(n):f$1(n);}function T$1(n){(!n.__d&&(n.__d=!0)&&r$1.push(n)&&!$$1.__r++||o!==l$1.debounceRendering)&&((o=l$1.debounceRendering)||C$1)($$1);}function $$1(){var n,l,u,i,t,o,f,e;for(r$1.sort(function(n,l){return n.__v.__b-l.__v.__b});n=r$1.shift();)n.__d&&(l=r$1.length,i=void 0,t=void 0,f=(o=(u=n).__v).__e,(e=u.__P)&&(i=[],(t=h({},o)).__v=o.__v+1,M(e,o,t,u.__n,void 0!==e.ownerSVGElement,null!=o.__h?[f]:null,i,null==f?A(o):f,o.__h),N(i,o),o.__e!=f&&P$1(o)),r$1.length>l&&r$1.sort(function(n,l){return n.__v.__b-l.__v.__b}));$$1.__r=0;}function H$1(n,l,u,i,t,r,o,f,e,a){var h,v,y,d,k,b,g,m=i&&i.__k||s,w=m.length;for(u.__k=[],h=0;h<l.length;h++)if(null!=(d=u.__k[h]=null==(d=l[h])||"boolean"==typeof d?null:"string"==typeof d||"number"==typeof d||"bigint"==typeof d?p(null,d,null,null,d):Array.isArray(d)?p(_,{children:d},null,null,null):d.__b>0?p(d.type,d.props,d.key,d.ref?d.ref:null,d.__v):d)){if(d.__=u,d.__b=u.__b+1,null===(y=m[h])||y&&d.key==y.key&&d.type===y.type)m[h]=void 0;else for(v=0;v<w;v++){if((y=m[v])&&d.key==y.key&&d.type===y.type){m[v]=void 0;break}y=null;}M(n,d,y=y||c$1,t,r,o,f,e,a),k=d.__e,(v=d.ref)&&y.ref!=v&&(g||(g=[]),y.ref&&g.push(y.ref,null,d),g.push(v,d.__c||k,d)),null!=k?(null==b&&(b=k),"function"==typeof d.type&&d.__k===y.__k?d.__d=e=I$1(d,e,n):e=z$1(n,d,y,m,k,e),"function"==typeof u.type&&(u.__d=e)):e&&y.__e==e&&e.parentNode!=n&&(e=A(y));}for(u.__e=b,h=w;h--;)null!=m[h]&&("function"==typeof u.type&&null!=m[h].__e&&m[h].__e==u.__d&&(u.__d=L$1(i).nextSibling),q(m[h],m[h]));if(g)for(h=0;h<g.length;h++)S(g[h],g[++h],g[++h]);}function I$1(n,l,u){for(var i,t=n.__k,r=0;t&&r<t.length;r++)(i=t[r])&&(i.__=n,l="function"==typeof i.type?I$1(i,l,u):z$1(u,i,i,t,i.__e,l));return l}function j$2(n,l){return l=l||[],null==n||"boolean"==typeof n||(Array.isArray(n)?n.some(function(n){j$2(n,l);}):l.push(n)),l}function z$1(n,l,u,i,t,r){var o,f,e;if(void 0!==l.__d)o=l.__d,l.__d=void 0;else if(null==u||t!=r||null==t.parentNode)n:if(null==r||r.parentNode!==n)n.appendChild(t),o=null;else {for(f=r,e=0;(f=f.nextSibling)&&e<i.length;e+=1)if(f==t)break n;n.insertBefore(t,r),o=r;}return void 0!==o?o:t.nextSibling}function L$1(n){var l,u,i;if(null==n.type||"string"==typeof n.type)return n.__e;if(n.__k)for(l=n.__k.length-1;l>=0;l--)if((u=n.__k[l])&&(i=L$1(u)))return i;return null}function M(n,u,i,t,r,o,f,e,c){var s,a,v,y,p,d,k,b,g,m,w,A,P,C,T,$=u.type;if(void 0!==u.constructor)return null;null!=i.__h&&(c=i.__h,e=u.__e=i.__e,u.__h=null,o=[e]),(s=l$1.__b)&&s(u);try{n:if("function"==typeof $){if(b=u.props,g=(s=$.contextType)&&t[s.__c],m=s?g?g.props.value:s.__:t,i.__c?k=(a=u.__c=i.__c).__=a.__E:("prototype"in $&&$.prototype.render?u.__c=a=new $(b,m):(u.__c=a=new x$1(b,m),a.constructor=$,a.render=B$1),g&&g.sub(a),a.props=b,a.state||(a.state={}),a.context=m,a.__n=t,v=a.__d=!0,a.__h=[],a._sb=[]),null==a.__s&&(a.__s=a.state),null!=$.getDerivedStateFromProps&&(a.__s==a.state&&(a.__s=h({},a.__s)),h(a.__s,$.getDerivedStateFromProps(b,a.__s))),y=a.props,p=a.state,a.__v=u,v)null==$.getDerivedStateFromProps&&null!=a.componentWillMount&&a.componentWillMount(),null!=a.componentDidMount&&a.__h.push(a.componentDidMount);else {if(null==$.getDerivedStateFromProps&&b!==y&&null!=a.componentWillReceiveProps&&a.componentWillReceiveProps(b,m),!a.__e&&null!=a.shouldComponentUpdate&&!1===a.shouldComponentUpdate(b,a.__s,m)||u.__v===i.__v){for(u.__v!==i.__v&&(a.props=b,a.state=a.__s,a.__d=!1),u.__e=i.__e,u.__k=i.__k,u.__k.forEach(function(n){n&&(n.__=u);}),w=0;w<a._sb.length;w++)a.__h.push(a._sb[w]);a._sb=[],a.__h.length&&f.push(a);break n}null!=a.componentWillUpdate&&a.componentWillUpdate(b,a.__s,m),null!=a.componentDidUpdate&&a.__h.push(function(){a.componentDidUpdate(y,p,d);});}if(a.context=m,a.props=b,a.__P=n,A=l$1.__r,P=0,"prototype"in $&&$.prototype.render){for(a.state=a.__s,a.__d=!1,A&&A(u),s=a.render(a.props,a.state,a.context),C=0;C<a._sb.length;C++)a.__h.push(a._sb[C]);a._sb=[];}else do{a.__d=!1,A&&A(u),s=a.render(a.props,a.state,a.context),a.state=a.__s;}while(a.__d&&++P<25);a.state=a.__s,null!=a.getChildContext&&(t=h(h({},t),a.getChildContext())),v||null==a.getSnapshotBeforeUpdate||(d=a.getSnapshotBeforeUpdate(y,p)),T=null!=s&&s.type===_&&null==s.key?s.props.children:s,H$1(n,Array.isArray(T)?T:[T],u,i,t,r,o,f,e,c),a.base=u.__e,u.__h=null,a.__h.length&&f.push(a),k&&(a.__E=a.__=null),a.__e=!1;}else null==o&&u.__v===i.__v?(u.__k=i.__k,u.__e=i.__e):u.__e=O(i.__e,u,i,t,r,o,f,c);(s=l$1.diffed)&&s(u);}catch(n){u.__v=null,(c||null!=o)&&(u.__e=e,u.__h=!!c,o[o.indexOf(e)]=null),l$1.__e(n,u,i);}}function N(n,u){l$1.__c&&l$1.__c(u,n),n.some(function(u){try{n=u.__h,u.__h=[],n.some(function(n){n.call(u);});}catch(n){l$1.__e(n,u.__v);}});}function O(l,u,i,t,r,o,f,e){var s,a,h,y=i.props,p=u.props,d=u.type,_=0;if("svg"===d&&(r=!0),null!=o)for(;_<o.length;_++)if((s=o[_])&&"setAttribute"in s==!!d&&(d?s.localName===d:3===s.nodeType)){l=s,o[_]=null;break}if(null==l){if(null===d)return document.createTextNode(p);l=r?document.createElementNS("http://www.w3.org/2000/svg",d):document.createElement(d,p.is&&p),o=null,e=!1;}if(null===d)y===p||e&&l.data===p||(l.data=p);else {if(o=o&&n.call(l.childNodes),a=(y=i.props||c$1).dangerouslySetInnerHTML,h=p.dangerouslySetInnerHTML,!e){if(null!=o)for(y={},_=0;_<l.attributes.length;_++)y[l.attributes[_].name]=l.attributes[_].value;(h||a)&&(h&&(a&&h.__html==a.__html||h.__html===l.innerHTML)||(l.innerHTML=h&&h.__html||""));}if(k$1(l,p,y,r,e),h)u.__k=[];else if(_=u.props.children,H$1(l,Array.isArray(_)?_:[_],u,i,t,r&&"foreignObject"!==d,o,f,o?o[0]:i.__k&&A(i,0),e),null!=o)for(_=o.length;_--;)null!=o[_]&&v$1(o[_]);e||("value"in p&&void 0!==(_=p.value)&&(_!==l.value||"progress"===d&&!_||"option"===d&&_!==y.value)&&g$2(l,"value",_,y.value,!1),"checked"in p&&void 0!==(_=p.checked)&&_!==l.checked&&g$2(l,"checked",_,y.checked,!1));}return l}function S(n,u,i){try{"function"==typeof n?n(u):n.current=u;}catch(n){l$1.__e(n,i);}}function q(n,u,i){var t,r;if(l$1.unmount&&l$1.unmount(n),(t=n.ref)&&(t.current&&t.current!==n.__e||S(t,null,u)),null!=(t=n.__c)){if(t.componentWillUnmount)try{t.componentWillUnmount();}catch(n){l$1.__e(n,u);}t.base=t.__P=null,n.__c=void 0;}if(t=n.__k)for(r=0;r<t.length;r++)t[r]&&q(t[r],u,i||"function"!=typeof n.type);i||null==n.__e||v$1(n.__e),n.__=n.__e=n.__d=void 0;}function B$1(n,l,u){return this.constructor(n,u)}function D$1(u,i,t){var r,o,f;l$1.__&&l$1.__(u,i),o=(r="function"==typeof t)?null:t&&t.__k||i.__k,f=[],M(i,u=(!r&&t||i).__k=y(_,null,[u]),o||c$1,c$1,void 0!==i.ownerSVGElement,!r&&t?[t]:o?null:i.firstChild?n.call(i.childNodes):null,f,!r&&t?t:o?o.__e:i.firstChild,r),N(f,u);}function E(n,l){D$1(n,l,E);}function F$1(l,u,i){var t,r,o,f=h({},l.props);for(o in u)"key"==o?t=u[o]:"ref"==o?r=u[o]:f[o]=u[o];return arguments.length>2&&(f.children=arguments.length>3?n.call(arguments,2):i),p(l.type,f,t||l.key,r||l.ref,null)}function G$1(n,l){var u={__c:l="__cC"+e$1++,__:n,Consumer:function(n,l){return n.children(l)},Provider:function(n){var u,i;return this.getChildContext||(u=[],(i={})[l]=this,this.getChildContext=function(){return i},this.shouldComponentUpdate=function(n){this.props.value!==n.value&&u.some(function(n){n.__e=!0,T$1(n);});},this.sub=function(n){u.push(n);var l=n.componentWillUnmount;n.componentWillUnmount=function(){u.splice(u.indexOf(n),1),l&&l.call(n);};}),n.children}};return u.Provider.__=u.Consumer.contextType=u}n=s.slice,l$1={__e:function(n,l,u,i){for(var t,r,o;l=l.__;)if((t=l.__c)&&!t.__)try{if((r=t.constructor)&&null!=r.getDerivedStateFromError&&(t.setState(r.getDerivedStateFromError(n)),o=t.__d),null!=t.componentDidCatch&&(t.componentDidCatch(n,i||{}),o=t.__d),o)return t.__E=t}catch(l){n=l;}throw n}},u$1=0,i$1=function(n){return null!=n&&void 0===n.constructor},t=!1,x$1.prototype.setState=function(n,l){var u;u=null!=this.__s&&this.__s!==this.state?this.__s:this.__s=h({},this.state),"function"==typeof n&&(n=n(h({},u),this.props)),n&&h(u,n),null!=n&&this.__v&&(l&&this._sb.push(l),T$1(this));},x$1.prototype.forceUpdate=function(n){this.__v&&(this.__e=!0,n&&this.__h.push(n),T$1(this));},x$1.prototype.render=_,r$1=[],f$1="function"==typeof Promise?Promise.prototype.then.bind(Promise.resolve()):setTimeout,$$1.__r=0,e$1=0;

    var r,u,i,f=[],c=[],e=l$1.__b,a=l$1.__r,v=l$1.diffed,l=l$1.__c,m=l$1.unmount;function b(){for(var t;t=f.shift();)if(t.__P&&t.__H)try{t.__H.__h.forEach(k),t.__H.__h.forEach(w$1),t.__H.__h=[];}catch(r){t.__H.__h=[],l$1.__e(r,t.__v);}}l$1.__b=function(n){r=null,e&&e(n);},l$1.__r=function(n){a&&a(n);var i=(r=n.__c).__H;i&&(u===r?(i.__h=[],r.__h=[],i.__.forEach(function(n){n.__N&&(n.__=n.__N),n.__V=c,n.__N=n.i=void 0;})):(i.__h.forEach(k),i.__h.forEach(w$1),i.__h=[])),u=r;},l$1.diffed=function(t){v&&v(t);var o=t.__c;o&&o.__H&&(o.__H.__h.length&&(1!==f.push(o)&&i===l$1.requestAnimationFrame||((i=l$1.requestAnimationFrame)||j$1)(b)),o.__H.__.forEach(function(n){n.i&&(n.__H=n.i),n.__V!==c&&(n.__=n.__V),n.i=void 0,n.__V=c;})),u=r=null;},l$1.__c=function(t,r){r.some(function(t){try{t.__h.forEach(k),t.__h=t.__h.filter(function(n){return !n.__||w$1(n)});}catch(u){r.some(function(n){n.__h&&(n.__h=[]);}),r=[],l$1.__e(u,t.__v);}}),l&&l(t,r);},l$1.unmount=function(t){m&&m(t);var r,u=t.__c;u&&u.__H&&(u.__H.__.forEach(function(n){try{k(n);}catch(n){r=n;}}),u.__H=void 0,r&&l$1.__e(r,u.__v));};var g$1="function"==typeof requestAnimationFrame;function j$1(n){var t,r=function(){clearTimeout(u),g$1&&cancelAnimationFrame(t),setTimeout(n);},u=setTimeout(r,100);g$1&&(t=requestAnimationFrame(r));}function k(n){var t=r,u=n.__c;"function"==typeof u&&(n.__c=void 0,u()),r=t;}function w$1(n){var t=r;n.__c=n.__(),r=t;}

    function g(n,t){for(var e in t)n[e]=t[e];return n}function C(n,t){for(var e in n)if("__source"!==e&&!(e in t))return !0;for(var r in t)if("__source"!==r&&n[r]!==t[r])return !0;return !1}function w(n){this.props=n;}(w.prototype=new x$1).isPureReactComponent=!0,w.prototype.shouldComponentUpdate=function(n,t){return C(this.props,n)||C(this.state,t)};var x=l$1.__b;l$1.__b=function(n){n.type&&n.type.__f&&n.ref&&(n.props.ref=n.ref,n.ref=null),x&&x(n);};var T=l$1.__e;l$1.__e=function(n,t,e,r){if(n.then)for(var u,o=t;o=o.__;)if((u=o.__c)&&u.__c)return null==t.__e&&(t.__e=e.__e,t.__k=e.__k),u.__c(n,t);T(n,t,e,r);};var I=l$1.unmount;function L(n,t,e){return n&&(n.__c&&n.__c.__H&&(n.__c.__H.__.forEach(function(n){"function"==typeof n.__c&&n.__c();}),n.__c.__H=null),null!=(n=g({},n)).__c&&(n.__c.__P===e&&(n.__c.__P=t),n.__c=null),n.__k=n.__k&&n.__k.map(function(n){return L(n,t,e)})),n}function U(n,t,e){return n&&(n.__v=null,n.__k=n.__k&&n.__k.map(function(n){return U(n,t,e)}),n.__c&&n.__c.__P===t&&(n.__e&&e.insertBefore(n.__e,n.__d),n.__c.__e=!0,n.__c.__P=e)),n}function D(){this.__u=0,this.t=null,this.__b=null;}function F(n){var t=n.__.__c;return t&&t.__a&&t.__a(n)}function V(){this.u=null,this.o=null;}l$1.unmount=function(n){var t=n.__c;t&&t.__R&&t.__R(),t&&!0===n.__h&&(n.type=null),I&&I(n);},(D.prototype=new x$1).__c=function(n,t){var e=t.__c,r=this;null==r.t&&(r.t=[]),r.t.push(e);var u=F(r.__v),o=!1,i=function(){o||(o=!0,e.__R=null,u?u(l):l());};e.__R=i;var l=function(){if(!--r.__u){if(r.state.__a){var n=r.state.__a;r.__v.__k[0]=U(n,n.__c.__P,n.__c.__O);}var t;for(r.setState({__a:r.__b=null});t=r.t.pop();)t.forceUpdate();}},c=!0===t.__h;r.__u++||c||r.setState({__a:r.__b=r.__v.__k[0]}),n.then(i,i);},D.prototype.componentWillUnmount=function(){this.t=[];},D.prototype.render=function(n,e){if(this.__b){if(this.__v.__k){var r=document.createElement("div"),o=this.__v.__k[0].__c;this.__v.__k[0]=L(this.__b,r,o.__O=o.__P);}this.__b=null;}var i=e.__a&&y(_,null,n.fallback);return i&&(i.__h=null),[y(_,null,e.__a?null:n.children),i]};var W=function(n,t,e){if(++e[1]===e[0]&&n.o.delete(t),n.props.revealOrder&&("t"!==n.props.revealOrder[0]||!n.o.size))for(e=n.u;e;){for(;e.length>3;)e.pop()();if(e[1]<e[0])break;n.u=e=e[2];}};function P(n){return this.getChildContext=function(){return n.context},n.children}function $(n){var e=this,r=n.i;e.componentWillUnmount=function(){D$1(null,e.l),e.l=null,e.i=null;},e.i&&e.i!==r&&e.componentWillUnmount(),n.__v?(e.l||(e.i=r,e.l={nodeType:1,parentNode:r,childNodes:[],appendChild:function(n){this.childNodes.push(n),e.i.appendChild(n);},insertBefore:function(n,t){this.childNodes.push(n),e.i.appendChild(n);},removeChild:function(n){this.childNodes.splice(this.childNodes.indexOf(n)>>>1,1),e.i.removeChild(n);}}),D$1(y(P,{context:e.context},n.__v),e.l)):e.l&&e.componentWillUnmount();}function j(n,e){var r=y($,{__v:n,i:e});return r.containerInfo=e,r}(V.prototype=new x$1).__a=function(n){var t=this,e=F(t.__v),r=t.o.get(n);return r[0]++,function(u){var o=function(){t.props.revealOrder?(r.push(u),W(t,n,r)):u();};e?e(o):o();}},V.prototype.render=function(n){this.u=null,this.o=new Map;var t=j$2(n.children);n.revealOrder&&"b"===n.revealOrder[0]&&t.reverse();for(var e=t.length;e--;)this.o.set(t[e],this.u=[1,0,this.u]);return n.children},V.prototype.componentDidUpdate=V.prototype.componentDidMount=function(){var n=this;this.o.forEach(function(t,e){W(n,e,t);});};var z="undefined"!=typeof Symbol&&Symbol.for&&Symbol.for("react.element")||60103,B=/^(?:accent|alignment|arabic|baseline|cap|clip(?!PathU)|color|dominant|fill|flood|font|glyph(?!R)|horiz|image|letter|lighting|marker(?!H|W|U)|overline|paint|pointer|shape|stop|strikethrough|stroke|text(?!L)|transform|underline|unicode|units|v|vector|vert|word|writing|x(?!C))[A-Z]/,H="undefined"!=typeof document,Z=function(n){return ("undefined"!=typeof Symbol&&"symbol"==typeof Symbol()?/fil|che|rad/i:/fil|che|ra/i).test(n)};x$1.prototype.isReactComponent={},["componentWillMount","componentWillReceiveProps","componentWillUpdate"].forEach(function(t){Object.defineProperty(x$1.prototype,t,{configurable:!0,get:function(){return this["UNSAFE_"+t]},set:function(n){Object.defineProperty(this,t,{configurable:!0,writable:!0,value:n});}});});var G=l$1.event;function J(){}function K(){return this.cancelBubble}function Q(){return this.defaultPrevented}l$1.event=function(n){return G&&(n=G(n)),n.persist=J,n.isPropagationStopped=K,n.isDefaultPrevented=Q,n.nativeEvent=n};var nn={configurable:!0,get:function(){return this.class}},tn=l$1.vnode;l$1.vnode=function(n){var t=n.type,e=n.props,u=e;if("string"==typeof t){var o=-1===t.indexOf("-");for(var i in u={},e){var l=e[i];H&&"children"===i&&"noscript"===t||"value"===i&&"defaultValue"in e&&null==l||("defaultValue"===i&&"value"in e&&null==e.value?i="value":"download"===i&&!0===l?l="":/ondoubleclick/i.test(i)?i="ondblclick":/^onchange(textarea|input)/i.test(i+t)&&!Z(e.type)?i="oninput":/^onfocus$/i.test(i)?i="onfocusin":/^onblur$/i.test(i)?i="onfocusout":/^on(Ani|Tra|Tou|BeforeInp|Compo)/.test(i)?i=i.toLowerCase():o&&B.test(i)?i=i.replace(/[A-Z0-9]/g,"-$&").toLowerCase():null===l&&(l=void 0),/^oninput$/i.test(i)&&(i=i.toLowerCase(),u[i]&&(i="oninputCapture")),u[i]=l);}"select"==t&&u.multiple&&Array.isArray(u.value)&&(u.value=j$2(e.children).forEach(function(n){n.props.selected=-1!=u.value.indexOf(n.props.value);})),"select"==t&&null!=u.defaultValue&&(u.value=j$2(e.children).forEach(function(n){n.props.selected=u.multiple?-1!=u.defaultValue.indexOf(n.props.value):u.defaultValue==n.props.value;})),n.props=u,e.class!=e.className&&(nn.enumerable="className"in e,null!=e.className&&(u.class=e.className),Object.defineProperty(u,"className",nn));}n.$$typeof=z,tn&&tn(n);};var en=l$1.__r;l$1.__r=function(n){en&&en(n),n.__c;};

    /*
    NOTE: this can be a public API, especially createElement for hooks.
    See examples/typescript-scheduler/src/index.ts
    */
    function flushSync(runBeforeFlush) {
        runBeforeFlush();
        let oldDebounceRendering = l$1.debounceRendering; // orig
        let callbackQ = [];
        function execCallbackSync(callback) {
            callbackQ.push(callback);
        }
        l$1.debounceRendering = execCallbackSync;
        D$1(y(FakeComponent, {}), document.createElement('div'));
        while (callbackQ.length) {
            callbackQ.shift()();
        }
        l$1.debounceRendering = oldDebounceRendering;
    }
    class FakeComponent extends x$1 {
        render() { return y('div', {}); }
        componentDidMount() { this.setState({}); }
    }
    // TODO: use preact/compat instead?
    function createContext(defaultValue) {
        let ContextType = G$1(defaultValue);
        let origProvider = ContextType.Provider;
        ContextType.Provider = function () {
            let isNew = !this.getChildContext;
            let children = origProvider.apply(this, arguments); // eslint-disable-line prefer-rest-params
            if (isNew) {
                let subs = [];
                this.shouldComponentUpdate = (_props) => {
                    if (this.props.value !== _props.value) {
                        subs.forEach((c) => {
                            c.context = _props.value;
                            c.forceUpdate();
                        });
                    }
                };
                this.sub = (c) => {
                    subs.push(c);
                    let old = c.componentWillUnmount;
                    c.componentWillUnmount = () => {
                        subs.splice(subs.indexOf(c), 1);
                        old && old.call(c);
                    };
                };
            }
            return children;
        };
        return ContextType;
    }

    var preact = {
        __proto__: null,
        flushSync: flushSync,
        createContext: createContext,
        createPortal: j,
        Component: x$1,
        Fragment: _,
        cloneElement: F$1,
        createElement: y,
        createRef: d,
        h: y,
        hydrate: E,
        get isValidElement () { return i$1; },
        get options () { return l$1; },
        render: D$1,
        toChildArray: j$2
    };

    class ScrollResponder {
        constructor(execFunc, emitter, scrollTime, scrollTimeReset) {
            this.execFunc = execFunc;
            this.emitter = emitter;
            this.scrollTime = scrollTime;
            this.scrollTimeReset = scrollTimeReset;
            this.handleScrollRequest = (request) => {
                this.queuedRequest = Object.assign({}, this.queuedRequest || {}, request);
                this.drain();
            };
            emitter.on('_scrollRequest', this.handleScrollRequest);
            this.fireInitialScroll();
        }
        detach() {
            this.emitter.off('_scrollRequest', this.handleScrollRequest);
        }
        update(isDatesNew) {
            if (isDatesNew && this.scrollTimeReset) {
                this.fireInitialScroll(); // will drain
            }
            else {
                this.drain();
            }
        }
        fireInitialScroll() {
            this.handleScrollRequest({
                time: this.scrollTime,
            });
        }
        drain() {
            if (this.queuedRequest && this.execFunc(this.queuedRequest)) {
                this.queuedRequest = null;
            }
        }
    }

    const ViewContextType = createContext({}); // for Components
    function buildViewContext(viewSpec, viewApi, viewOptions, dateProfileGenerator, dateEnv, nowManager, theme, pluginHooks, dispatch, getCurrentData, emitter, calendarApi, registerInteractiveComponent, unregisterInteractiveComponent) {
        return {
            dateEnv,
            nowManager,
            options: viewOptions,
            pluginHooks,
            emitter,
            dispatch,
            getCurrentData,
            calendarApi,
            viewSpec,
            viewApi,
            dateProfileGenerator,
            theme,
            isRtl: viewOptions.direction === 'rtl',
            addResizeHandler(handler) {
                emitter.on('_resize', handler);
            },
            removeResizeHandler(handler) {
                emitter.off('_resize', handler);
            },
            createScrollResponder(execFunc) {
                return new ScrollResponder(execFunc, emitter, createDuration(viewOptions.scrollTime), viewOptions.scrollTimeReset);
            },
            registerInteractiveComponent,
            unregisterInteractiveComponent,
        };
    }

    /* eslint max-classes-per-file: off */
    class PureComponent extends x$1 {
        // debug: boolean
        shouldComponentUpdate(nextProps, nextState) {
            const shouldUpdate = !compareObjs(this.props, nextProps, this.propEquality /*, this.debug */) ||
                !compareObjs(this.state, nextState, this.stateEquality /*, this.debug */);
            // if (this.debug && shouldUpdate) {
            //   console.log('shouldUpdate!')
            // }
            return shouldUpdate;
        }
        // HACK for freakin' React StrictMode
        safeSetState(newState) {
            if (!compareObjs(this.state, Object.assign(Object.assign({}, this.state), newState), this.stateEquality)) {
                this.setState(newState);
            }
        }
    }
    PureComponent.addPropsEquality = addPropsEquality;
    PureComponent.addStateEquality = addStateEquality;
    PureComponent.contextType = ViewContextType;
    PureComponent.prototype.propEquality = {};
    PureComponent.prototype.stateEquality = {};
    class BaseComponent extends PureComponent {
    }
    BaseComponent.contextType = ViewContextType;
    function addPropsEquality(propEquality) {
        let hash = Object.create(this.prototype.propEquality);
        Object.assign(hash, propEquality);
        this.prototype.propEquality = hash;
    }
    function addStateEquality(stateEquality) {
        let hash = Object.create(this.prototype.stateEquality);
        Object.assign(hash, stateEquality);
        this.prototype.stateEquality = hash;
    }
    // use other one
    function setRef(ref, current) {
        if (typeof ref === 'function') {
            ref(current);
        }
        else if (ref) {
            // see https://github.com/facebook/react/issues/13029
            ref.current = current;
        }
    }

    /*
    an INTERACTABLE date component

    PURPOSES:
    - hook up to fg, fill, and mirror renderers
    - interface for dragging and hits
    */
    class DateComponent extends BaseComponent {
        constructor() {
            super(...arguments);
            this.uid = guid();
        }
        // Hit System
        // -----------------------------------------------------------------------------------------------------------------
        prepareHits() {
        }
        queryHit(positionLeft, positionTop, elWidth, elHeight) {
            return null; // this should be abstract
        }
        // Pointer Interaction Utils
        // -----------------------------------------------------------------------------------------------------------------
        isValidSegDownEl(el) {
            return !this.props.eventDrag && // HACK
                !this.props.eventResize && // HACK
                !elementClosest(el, '.fc-event-mirror');
        }
        isValidDateDownEl(el) {
            return !elementClosest(el, '.fc-event:not(.fc-bg-event)') &&
                !elementClosest(el, '.fc-more-link') && // a "more.." link
                !elementClosest(el, 'a[data-navlink]') && // a clickable nav link
                !elementClosest(el, '.fc-popover'); // hack
        }
    }

    class DateProfileGenerator {
        constructor(props) {
            this.props = props;
            this.initHiddenDays();
        }
        /* Date Range Computation
        ------------------------------------------------------------------------------------------------------------------*/
        // Builds a structure with info about what the dates/ranges will be for the "prev" view.
        buildPrev(currentDateProfile, currentDate, forceToValid) {
            let { dateEnv } = this.props;
            let prevDate = dateEnv.subtract(dateEnv.startOf(currentDate, currentDateProfile.currentRangeUnit), // important for start-of-month
            currentDateProfile.dateIncrement);
            return this.build(prevDate, -1, forceToValid);
        }
        // Builds a structure with info about what the dates/ranges will be for the "next" view.
        buildNext(currentDateProfile, currentDate, forceToValid) {
            let { dateEnv } = this.props;
            let nextDate = dateEnv.add(dateEnv.startOf(currentDate, currentDateProfile.currentRangeUnit), // important for start-of-month
            currentDateProfile.dateIncrement);
            return this.build(nextDate, 1, forceToValid);
        }
        // Builds a structure holding dates/ranges for rendering around the given date.
        // Optional direction param indicates whether the date is being incremented/decremented
        // from its previous value. decremented = -1, incremented = 1 (default).
        build(currentDate, direction, forceToValid = true) {
            let { props } = this;
            let validRange;
            let currentInfo;
            let isRangeAllDay;
            let renderRange;
            let activeRange;
            let isValid;
            validRange = this.buildValidRange();
            validRange = this.trimHiddenDays(validRange);
            if (forceToValid) {
                currentDate = constrainMarkerToRange(currentDate, validRange);
            }
            currentInfo = this.buildCurrentRangeInfo(currentDate, direction);
            isRangeAllDay = /^(year|month|week|day)$/.test(currentInfo.unit);
            renderRange = this.buildRenderRange(this.trimHiddenDays(currentInfo.range), currentInfo.unit, isRangeAllDay);
            renderRange = this.trimHiddenDays(renderRange);
            activeRange = renderRange;
            if (!props.showNonCurrentDates) {
                activeRange = intersectRanges(activeRange, currentInfo.range);
            }
            activeRange = this.adjustActiveRange(activeRange);
            activeRange = intersectRanges(activeRange, validRange); // might return null
            // it's invalid if the originally requested date is not contained,
            // or if the range is completely outside of the valid range.
            isValid = rangesIntersect(currentInfo.range, validRange);
            // HACK: constrain to render-range so `currentDate` is more useful to view rendering
            if (!rangeContainsMarker(renderRange, currentDate)) {
                currentDate = renderRange.start;
            }
            return {
                currentDate,
                // constraint for where prev/next operations can go and where events can be dragged/resized to.
                // an object with optional start and end properties.
                validRange,
                // range the view is formally responsible for.
                // for example, a month view might have 1st-31st, excluding padded dates
                currentRange: currentInfo.range,
                // name of largest unit being displayed, like "month" or "week"
                currentRangeUnit: currentInfo.unit,
                isRangeAllDay,
                // dates that display events and accept drag-n-drop
                // will be `null` if no dates accept events
                activeRange,
                // date range with a rendered skeleton
                // includes not-active days that need some sort of DOM
                renderRange,
                // Duration object that denotes the first visible time of any given day
                slotMinTime: props.slotMinTime,
                // Duration object that denotes the exclusive visible end time of any given day
                slotMaxTime: props.slotMaxTime,
                isValid,
                // how far the current date will move for a prev/next operation
                dateIncrement: this.buildDateIncrement(currentInfo.duration),
                // pass a fallback (might be null) ^
            };
        }
        // Builds an object with optional start/end properties.
        // Indicates the minimum/maximum dates to display.
        // not responsible for trimming hidden days.
        buildValidRange() {
            let input = this.props.validRangeInput;
            let simpleInput = typeof input === 'function'
                ? input.call(this.props.calendarApi, this.props.dateEnv.toDate(this.props.nowManager.getDateMarker()))
                : input;
            return this.refineRange(simpleInput) ||
                { start: null, end: null }; // completely open-ended
        }
        // Builds a structure with info about the "current" range, the range that is
        // highlighted as being the current month for example.
        // See build() for a description of `direction`.
        // Guaranteed to have `range` and `unit` properties. `duration` is optional.
        buildCurrentRangeInfo(date, direction) {
            let { props } = this;
            let duration = null;
            let unit = null;
            let range = null;
            let dayCount;
            if (props.duration) {
                duration = props.duration;
                unit = props.durationUnit;
                range = this.buildRangeFromDuration(date, direction, duration, unit);
            }
            else if ((dayCount = this.props.dayCount)) {
                unit = 'day';
                range = this.buildRangeFromDayCount(date, direction, dayCount);
            }
            else if ((range = this.buildCustomVisibleRange(date))) {
                unit = props.dateEnv.greatestWholeUnit(range.start, range.end).unit;
            }
            else {
                duration = this.getFallbackDuration();
                unit = greatestDurationDenominator(duration).unit;
                range = this.buildRangeFromDuration(date, direction, duration, unit);
            }
            return { duration, unit, range };
        }
        getFallbackDuration() {
            return createDuration({ day: 1 });
        }
        // Returns a new activeRange to have time values (un-ambiguate)
        // slotMinTime or slotMaxTime causes the range to expand.
        adjustActiveRange(range) {
            let { dateEnv, usesMinMaxTime, slotMinTime, slotMaxTime } = this.props;
            let { start, end } = range;
            if (usesMinMaxTime) {
                // expand active range if slotMinTime is negative (why not when positive?)
                if (asRoughDays(slotMinTime) < 0) {
                    start = startOfDay(start); // necessary?
                    start = dateEnv.add(start, slotMinTime);
                }
                // expand active range if slotMaxTime is beyond one day (why not when negative?)
                if (asRoughDays(slotMaxTime) > 1) {
                    end = startOfDay(end); // necessary?
                    end = addDays(end, -1);
                    end = dateEnv.add(end, slotMaxTime);
                }
            }
            return { start, end };
        }
        // Builds the "current" range when it is specified as an explicit duration.
        // `unit` is the already-computed greatestDurationDenominator unit of duration.
        buildRangeFromDuration(date, direction, duration, unit) {
            let { dateEnv, dateAlignment } = this.props;
            let start;
            let end;
            let res;
            // compute what the alignment should be
            if (!dateAlignment) {
                let { dateIncrement } = this.props;
                if (dateIncrement) {
                    // use the smaller of the two units
                    if (asRoughMs(dateIncrement) < asRoughMs(duration)) {
                        dateAlignment = greatestDurationDenominator(dateIncrement).unit;
                    }
                    else {
                        dateAlignment = unit;
                    }
                }
                else {
                    dateAlignment = unit;
                }
            }
            // if the view displays a single day or smaller
            if (asRoughDays(duration) <= 1) {
                if (this.isHiddenDay(start)) {
                    start = this.skipHiddenDays(start, direction);
                    start = startOfDay(start);
                }
            }
            function computeRes() {
                start = dateEnv.startOf(date, dateAlignment);
                end = dateEnv.add(start, duration);
                res = { start, end };
            }
            computeRes();
            // if range is completely enveloped by hidden days, go past the hidden days
            if (!this.trimHiddenDays(res)) {
                date = this.skipHiddenDays(date, direction);
                computeRes();
            }
            return res;
        }
        // Builds the "current" range when a dayCount is specified.
        buildRangeFromDayCount(date, direction, dayCount) {
            let { dateEnv, dateAlignment } = this.props;
            let runningCount = 0;
            let start = date;
            let end;
            if (dateAlignment) {
                start = dateEnv.startOf(start, dateAlignment);
            }
            start = startOfDay(start);
            start = this.skipHiddenDays(start, direction);
            end = start;
            do {
                end = addDays(end, 1);
                if (!this.isHiddenDay(end)) {
                    runningCount += 1;
                }
            } while (runningCount < dayCount);
            return { start, end };
        }
        // Builds a normalized range object for the "visible" range,
        // which is a way to define the currentRange and activeRange at the same time.
        buildCustomVisibleRange(date) {
            let { props } = this;
            let input = props.visibleRangeInput;
            let simpleInput = typeof input === 'function'
                ? input.call(props.calendarApi, props.dateEnv.toDate(date))
                : input;
            let range = this.refineRange(simpleInput);
            if (range && (range.start == null || range.end == null)) {
                return null;
            }
            return range;
        }
        // Computes the range that will represent the element/cells for *rendering*,
        // but which may have voided days/times.
        // not responsible for trimming hidden days.
        buildRenderRange(currentRange, currentRangeUnit, isRangeAllDay) {
            return currentRange;
        }
        // Compute the duration value that should be added/substracted to the current date
        // when a prev/next operation happens.
        buildDateIncrement(fallback) {
            let { dateIncrement } = this.props;
            let customAlignment;
            if (dateIncrement) {
                return dateIncrement;
            }
            if ((customAlignment = this.props.dateAlignment)) {
                return createDuration(1, customAlignment);
            }
            if (fallback) {
                return fallback;
            }
            return createDuration({ days: 1 });
        }
        refineRange(rangeInput) {
            if (rangeInput) {
                let range = parseRange(rangeInput, this.props.dateEnv);
                if (range) {
                    range = computeVisibleDayRange(range);
                }
                return range;
            }
            return null;
        }
        /* Hidden Days
        ------------------------------------------------------------------------------------------------------------------*/
        // Initializes internal variables related to calculating hidden days-of-week
        initHiddenDays() {
            let hiddenDays = this.props.hiddenDays || []; // array of day-of-week indices that are hidden
            let isHiddenDayHash = []; // is the day-of-week hidden? (hash with day-of-week-index -> bool)
            let dayCnt = 0;
            let i;
            if (this.props.weekends === false) {
                hiddenDays.push(0, 6); // 0=sunday, 6=saturday
            }
            for (i = 0; i < 7; i += 1) {
                if (!(isHiddenDayHash[i] = hiddenDays.indexOf(i) !== -1)) {
                    dayCnt += 1;
                }
            }
            if (!dayCnt) {
                throw new Error('invalid hiddenDays'); // all days were hidden? bad.
            }
            this.isHiddenDayHash = isHiddenDayHash;
        }
        // Remove days from the beginning and end of the range that are computed as hidden.
        // If the whole range is trimmed off, returns null
        trimHiddenDays(range) {
            let { start, end } = range;
            if (start) {
                start = this.skipHiddenDays(start);
            }
            if (end) {
                end = this.skipHiddenDays(end, -1, true);
            }
            if (start == null || end == null || start < end) {
                return { start, end };
            }
            return null;
        }
        // Is the current day hidden?
        // `day` is a day-of-week index (0-6), or a Date (used for UTC)
        isHiddenDay(day) {
            if (day instanceof Date) {
                day = day.getUTCDay();
            }
            return this.isHiddenDayHash[day];
        }
        // Incrementing the current day until it is no longer a hidden day, returning a copy.
        // DOES NOT CONSIDER validRange!
        // If the initial value of `date` is not a hidden day, don't do anything.
        // Pass `isExclusive` as `true` if you are dealing with an end date.
        // `inc` defaults to `1` (increment one day forward each time)
        skipHiddenDays(date, inc = 1, isExclusive = false) {
            while (this.isHiddenDayHash[(date.getUTCDay() + (isExclusive ? inc : 0) + 7) % 7]) {
                date = addDays(date, inc);
            }
            return date;
        }
    }

    function triggerDateSelect(selection, pev, context) {
        context.emitter.trigger('select', Object.assign(Object.assign({}, buildDateSpanApiWithContext(selection, context)), { jsEvent: pev ? pev.origEvent : null, view: context.viewApi || context.calendarApi.view }));
    }
    function triggerDateUnselect(pev, context) {
        context.emitter.trigger('unselect', {
            jsEvent: pev ? pev.origEvent : null,
            view: context.viewApi || context.calendarApi.view,
        });
    }
    function buildDateSpanApiWithContext(dateSpan, context) {
        let props = {};
        for (let transform of context.pluginHooks.dateSpanTransforms) {
            Object.assign(props, transform(dateSpan, context));
        }
        Object.assign(props, buildDateSpanApi(dateSpan, context.dateEnv));
        return props;
    }
    // Given an event's allDay status and start date, return what its fallback end date should be.
    // TODO: rename to computeDefaultEventEnd
    function getDefaultEventEnd(allDay, marker, context) {
        let { dateEnv, options } = context;
        let end = marker;
        if (allDay) {
            end = startOfDay(end);
            end = dateEnv.add(end, options.defaultAllDayEventDuration);
        }
        else {
            end = dateEnv.add(end, options.defaultTimedEventDuration);
        }
        return end;
    }

    // applies the mutation to ALL defs/instances within the event store
    function applyMutationToEventStore(eventStore, eventConfigBase, mutation, context) {
        let eventConfigs = compileEventUis(eventStore.defs, eventConfigBase);
        let dest = createEmptyEventStore();
        for (let defId in eventStore.defs) {
            let def = eventStore.defs[defId];
            dest.defs[defId] = applyMutationToEventDef(def, eventConfigs[defId], mutation, context);
        }
        for (let instanceId in eventStore.instances) {
            let instance = eventStore.instances[instanceId];
            let def = dest.defs[instance.defId]; // important to grab the newly modified def
            dest.instances[instanceId] = applyMutationToEventInstance(instance, def, eventConfigs[instance.defId], mutation, context);
        }
        return dest;
    }
    function applyMutationToEventDef(eventDef, eventConfig, mutation, context) {
        let standardProps = mutation.standardProps || {};
        // if hasEnd has not been specified, guess a good value based on deltas.
        // if duration will change, there's no way the default duration will persist,
        // and thus, we need to mark the event as having a real end
        if (standardProps.hasEnd == null &&
            eventConfig.durationEditable &&
            (mutation.startDelta || mutation.endDelta)) {
            standardProps.hasEnd = true; // TODO: is this mutation okay?
        }
        let copy = Object.assign(Object.assign(Object.assign({}, eventDef), standardProps), { ui: Object.assign(Object.assign({}, eventDef.ui), standardProps.ui) });
        if (mutation.extendedProps) {
            copy.extendedProps = Object.assign(Object.assign({}, copy.extendedProps), mutation.extendedProps);
        }
        for (let applier of context.pluginHooks.eventDefMutationAppliers) {
            applier(copy, mutation, context);
        }
        if (!copy.hasEnd && context.options.forceEventDuration) {
            copy.hasEnd = true;
        }
        return copy;
    }
    function applyMutationToEventInstance(eventInstance, eventDef, // must first be modified by applyMutationToEventDef
    eventConfig, mutation, context) {
        let { dateEnv } = context;
        let forceAllDay = mutation.standardProps && mutation.standardProps.allDay === true;
        let clearEnd = mutation.standardProps && mutation.standardProps.hasEnd === false;
        let copy = Object.assign({}, eventInstance);
        if (forceAllDay) {
            copy.range = computeAlignedDayRange(copy.range);
        }
        if (mutation.datesDelta && eventConfig.startEditable) {
            copy.range = {
                start: dateEnv.add(copy.range.start, mutation.datesDelta),
                end: dateEnv.add(copy.range.end, mutation.datesDelta),
            };
        }
        if (mutation.startDelta && eventConfig.durationEditable) {
            copy.range = {
                start: dateEnv.add(copy.range.start, mutation.startDelta),
                end: copy.range.end,
            };
        }
        if (mutation.endDelta && eventConfig.durationEditable) {
            copy.range = {
                start: copy.range.start,
                end: dateEnv.add(copy.range.end, mutation.endDelta),
            };
        }
        if (clearEnd) {
            copy.range = {
                start: copy.range.start,
                end: getDefaultEventEnd(eventDef.allDay, copy.range.start, context),
            };
        }
        // in case event was all-day but the supplied deltas were not
        // better util for this?
        if (eventDef.allDay) {
            copy.range = {
                start: startOfDay(copy.range.start),
                end: startOfDay(copy.range.end),
            };
        }
        // handle invalid durations
        if (copy.range.end < copy.range.start) {
            copy.range.end = getDefaultEventEnd(eventDef.allDay, copy.range.start, context);
        }
        return copy;
    }

    class EventSourceImpl {
        constructor(context, internalEventSource) {
            this.context = context;
            this.internalEventSource = internalEventSource;
        }
        remove() {
            this.context.dispatch({
                type: 'REMOVE_EVENT_SOURCE',
                sourceId: this.internalEventSource.sourceId,
            });
        }
        refetch() {
            this.context.dispatch({
                type: 'FETCH_EVENT_SOURCES',
                sourceIds: [this.internalEventSource.sourceId],
                isRefetch: true,
            });
        }
        get id() {
            return this.internalEventSource.publicId;
        }
        get url() {
            return this.internalEventSource.meta.url;
        }
        get format() {
            return this.internalEventSource.meta.format; // TODO: bad. not guaranteed
        }
    }

    class EventImpl {
        // instance will be null if expressing a recurring event that has no current instances,
        // OR if trying to validate an incoming external event that has no dates assigned
        constructor(context, def, instance) {
            this._context = context;
            this._def = def;
            this._instance = instance || null;
        }
        /*
        TODO: make event struct more responsible for this
        */
        setProp(name, val) {
            if (name in EVENT_DATE_REFINERS) {
                console.warn('Could not set date-related prop \'name\'. Use one of the date-related methods instead.');
                // TODO: make proper aliasing system?
            }
            else if (name === 'id') {
                val = EVENT_NON_DATE_REFINERS[name](val);
                this.mutate({
                    standardProps: { publicId: val }, // hardcoded internal name
                });
            }
            else if (name in EVENT_NON_DATE_REFINERS) {
                val = EVENT_NON_DATE_REFINERS[name](val);
                this.mutate({
                    standardProps: { [name]: val },
                });
            }
            else if (name in EVENT_UI_REFINERS) {
                let ui = EVENT_UI_REFINERS[name](val);
                if (name === 'color') {
                    ui = { backgroundColor: val, borderColor: val };
                }
                else if (name === 'editable') {
                    ui = { startEditable: val, durationEditable: val };
                }
                else {
                    ui = { [name]: val };
                }
                this.mutate({
                    standardProps: { ui },
                });
            }
            else {
                console.warn(`Could not set prop '${name}'. Use setExtendedProp instead.`);
            }
        }
        setExtendedProp(name, val) {
            this.mutate({
                extendedProps: { [name]: val },
            });
        }
        setStart(startInput, options = {}) {
            let { dateEnv } = this._context;
            let start = dateEnv.createMarker(startInput);
            if (start && this._instance) { // TODO: warning if parsed bad
                let instanceRange = this._instance.range;
                let startDelta = diffDates(instanceRange.start, start, dateEnv, options.granularity); // what if parsed bad!?
                if (options.maintainDuration) {
                    this.mutate({ datesDelta: startDelta });
                }
                else {
                    this.mutate({ startDelta });
                }
            }
        }
        setEnd(endInput, options = {}) {
            let { dateEnv } = this._context;
            let end;
            if (endInput != null) {
                end = dateEnv.createMarker(endInput);
                if (!end) {
                    return; // TODO: warning if parsed bad
                }
            }
            if (this._instance) {
                if (end) {
                    let endDelta = diffDates(this._instance.range.end, end, dateEnv, options.granularity);
                    this.mutate({ endDelta });
                }
                else {
                    this.mutate({ standardProps: { hasEnd: false } });
                }
            }
        }
        setDates(startInput, endInput, options = {}) {
            let { dateEnv } = this._context;
            let standardProps = { allDay: options.allDay };
            let start = dateEnv.createMarker(startInput);
            let end;
            if (!start) {
                return; // TODO: warning if parsed bad
            }
            if (endInput != null) {
                end = dateEnv.createMarker(endInput);
                if (!end) { // TODO: warning if parsed bad
                    return;
                }
            }
            if (this._instance) {
                let instanceRange = this._instance.range;
                // when computing the diff for an event being converted to all-day,
                // compute diff off of the all-day values the way event-mutation does.
                if (options.allDay === true) {
                    instanceRange = computeAlignedDayRange(instanceRange);
                }
                let startDelta = diffDates(instanceRange.start, start, dateEnv, options.granularity);
                if (end) {
                    let endDelta = diffDates(instanceRange.end, end, dateEnv, options.granularity);
                    if (durationsEqual(startDelta, endDelta)) {
                        this.mutate({ datesDelta: startDelta, standardProps });
                    }
                    else {
                        this.mutate({ startDelta, endDelta, standardProps });
                    }
                }
                else { // means "clear the end"
                    standardProps.hasEnd = false;
                    this.mutate({ datesDelta: startDelta, standardProps });
                }
            }
        }
        moveStart(deltaInput) {
            let delta = createDuration(deltaInput);
            if (delta) { // TODO: warning if parsed bad
                this.mutate({ startDelta: delta });
            }
        }
        moveEnd(deltaInput) {
            let delta = createDuration(deltaInput);
            if (delta) { // TODO: warning if parsed bad
                this.mutate({ endDelta: delta });
            }
        }
        moveDates(deltaInput) {
            let delta = createDuration(deltaInput);
            if (delta) { // TODO: warning if parsed bad
                this.mutate({ datesDelta: delta });
            }
        }
        setAllDay(allDay, options = {}) {
            let standardProps = { allDay };
            let { maintainDuration } = options;
            if (maintainDuration == null) {
                maintainDuration = this._context.options.allDayMaintainDuration;
            }
            if (this._def.allDay !== allDay) {
                standardProps.hasEnd = maintainDuration;
            }
            this.mutate({ standardProps });
        }
        formatRange(formatInput) {
            let { dateEnv } = this._context;
            let instance = this._instance;
            let formatter = createFormatter(formatInput);
            if (this._def.hasEnd) {
                return dateEnv.formatRange(instance.range.start, instance.range.end, formatter, {
                    forcedStartTzo: instance.forcedStartTzo,
                    forcedEndTzo: instance.forcedEndTzo,
                });
            }
            return dateEnv.format(instance.range.start, formatter, {
                forcedTzo: instance.forcedStartTzo,
            });
        }
        mutate(mutation) {
            let instance = this._instance;
            if (instance) {
                let def = this._def;
                let context = this._context;
                let { eventStore } = context.getCurrentData();
                let relevantEvents = getRelevantEvents(eventStore, instance.instanceId);
                let eventConfigBase = {
                    '': {
                        display: '',
                        startEditable: true,
                        durationEditable: true,
                        constraints: [],
                        overlap: null,
                        allows: [],
                        backgroundColor: '',
                        borderColor: '',
                        textColor: '',
                        classNames: [],
                    },
                };
                relevantEvents = applyMutationToEventStore(relevantEvents, eventConfigBase, mutation, context);
                let oldEvent = new EventImpl(context, def, instance); // snapshot
                this._def = relevantEvents.defs[def.defId];
                this._instance = relevantEvents.instances[instance.instanceId];
                context.dispatch({
                    type: 'MERGE_EVENTS',
                    eventStore: relevantEvents,
                });
                context.emitter.trigger('eventChange', {
                    oldEvent,
                    event: this,
                    relatedEvents: buildEventApis(relevantEvents, context, instance),
                    revert() {
                        context.dispatch({
                            type: 'RESET_EVENTS',
                            eventStore, // the ORIGINAL store
                        });
                    },
                });
            }
        }
        remove() {
            let context = this._context;
            let asStore = eventApiToStore(this);
            context.dispatch({
                type: 'REMOVE_EVENTS',
                eventStore: asStore,
            });
            context.emitter.trigger('eventRemove', {
                event: this,
                relatedEvents: [],
                revert() {
                    context.dispatch({
                        type: 'MERGE_EVENTS',
                        eventStore: asStore,
                    });
                },
            });
        }
        get source() {
            let { sourceId } = this._def;
            if (sourceId) {
                return new EventSourceImpl(this._context, this._context.getCurrentData().eventSources[sourceId]);
            }
            return null;
        }
        get start() {
            return this._instance ?
                this._context.dateEnv.toDate(this._instance.range.start) :
                null;
        }
        get end() {
            return (this._instance && this._def.hasEnd) ?
                this._context.dateEnv.toDate(this._instance.range.end) :
                null;
        }
        get startStr() {
            let instance = this._instance;
            if (instance) {
                return this._context.dateEnv.formatIso(instance.range.start, {
                    omitTime: this._def.allDay,
                    forcedTzo: instance.forcedStartTzo,
                });
            }
            return '';
        }
        get endStr() {
            let instance = this._instance;
            if (instance && this._def.hasEnd) {
                return this._context.dateEnv.formatIso(instance.range.end, {
                    omitTime: this._def.allDay,
                    forcedTzo: instance.forcedEndTzo,
                });
            }
            return '';
        }
        // computable props that all access the def
        // TODO: find a TypeScript-compatible way to do this at scale
        get id() { return this._def.publicId; }
        get groupId() { return this._def.groupId; }
        get allDay() { return this._def.allDay; }
        get title() { return this._def.title; }
        get url() { return this._def.url; }
        get display() { return this._def.ui.display || 'auto'; } // bad. just normalize the type earlier
        get startEditable() { return this._def.ui.startEditable; }
        get durationEditable() { return this._def.ui.durationEditable; }
        get constraint() { return this._def.ui.constraints[0] || null; }
        get overlap() { return this._def.ui.overlap; }
        get allow() { return this._def.ui.allows[0] || null; }
        get backgroundColor() { return this._def.ui.backgroundColor; }
        get borderColor() { return this._def.ui.borderColor; }
        get textColor() { return this._def.ui.textColor; }
        // NOTE: user can't modify these because Object.freeze was called in event-def parsing
        get classNames() { return this._def.ui.classNames; }
        get extendedProps() { return this._def.extendedProps; }
        toPlainObject(settings = {}) {
            let def = this._def;
            let { ui } = def;
            let { startStr, endStr } = this;
            let res = {
                allDay: def.allDay,
            };
            if (def.title) {
                res.title = def.title;
            }
            if (startStr) {
                res.start = startStr;
            }
            if (endStr) {
                res.end = endStr;
            }
            if (def.publicId) {
                res.id = def.publicId;
            }
            if (def.groupId) {
                res.groupId = def.groupId;
            }
            if (def.url) {
                res.url = def.url;
            }
            if (ui.display && ui.display !== 'auto') {
                res.display = ui.display;
            }
            // TODO: what about recurring-event properties???
            // TODO: include startEditable/durationEditable/constraint/overlap/allow
            if (settings.collapseColor && ui.backgroundColor && ui.backgroundColor === ui.borderColor) {
                res.color = ui.backgroundColor;
            }
            else {
                if (ui.backgroundColor) {
                    res.backgroundColor = ui.backgroundColor;
                }
                if (ui.borderColor) {
                    res.borderColor = ui.borderColor;
                }
            }
            if (ui.textColor) {
                res.textColor = ui.textColor;
            }
            if (ui.classNames.length) {
                res.classNames = ui.classNames;
            }
            if (Object.keys(def.extendedProps).length) {
                if (settings.collapseExtendedProps) {
                    Object.assign(res, def.extendedProps);
                }
                else {
                    res.extendedProps = def.extendedProps;
                }
            }
            return res;
        }
        toJSON() {
            return this.toPlainObject();
        }
    }
    function eventApiToStore(eventApi) {
        let def = eventApi._def;
        let instance = eventApi._instance;
        return {
            defs: { [def.defId]: def },
            instances: instance
                ? { [instance.instanceId]: instance }
                : {},
        };
    }
    function buildEventApis(eventStore, context, excludeInstance) {
        let { defs, instances } = eventStore;
        let eventApis = [];
        let excludeInstanceId = excludeInstance ? excludeInstance.instanceId : '';
        for (let id in instances) {
            let instance = instances[id];
            let def = defs[instance.defId];
            if (instance.instanceId !== excludeInstanceId) {
                eventApis.push(new EventImpl(context, def, instance));
            }
        }
        return eventApis;
    }

    /*
    Specifying nextDayThreshold signals that all-day ranges should be sliced.
    */
    function sliceEventStore(eventStore, eventUiBases, framingRange, nextDayThreshold) {
        let inverseBgByGroupId = {};
        let inverseBgByDefId = {};
        let defByGroupId = {};
        let bgRanges = [];
        let fgRanges = [];
        let eventUis = compileEventUis(eventStore.defs, eventUiBases);
        for (let defId in eventStore.defs) {
            let def = eventStore.defs[defId];
            let ui = eventUis[def.defId];
            if (ui.display === 'inverse-background') {
                if (def.groupId) {
                    inverseBgByGroupId[def.groupId] = [];
                    if (!defByGroupId[def.groupId]) {
                        defByGroupId[def.groupId] = def;
                    }
                }
                else {
                    inverseBgByDefId[defId] = [];
                }
            }
        }
        for (let instanceId in eventStore.instances) {
            let instance = eventStore.instances[instanceId];
            let def = eventStore.defs[instance.defId];
            let ui = eventUis[def.defId];
            let origRange = instance.range;
            let normalRange = (!def.allDay && nextDayThreshold) ?
                computeVisibleDayRange(origRange, nextDayThreshold) :
                origRange;
            let slicedRange = intersectRanges(normalRange, framingRange);
            if (slicedRange) {
                if (ui.display === 'inverse-background') {
                    if (def.groupId) {
                        inverseBgByGroupId[def.groupId].push(slicedRange);
                    }
                    else {
                        inverseBgByDefId[instance.defId].push(slicedRange);
                    }
                }
                else if (ui.display !== 'none') {
                    (ui.display === 'background' ? bgRanges : fgRanges).push({
                        def,
                        ui,
                        instance,
                        range: slicedRange,
                        isStart: normalRange.start && normalRange.start.valueOf() === slicedRange.start.valueOf(),
                        isEnd: normalRange.end && normalRange.end.valueOf() === slicedRange.end.valueOf(),
                    });
                }
            }
        }
        for (let groupId in inverseBgByGroupId) { // BY GROUP
            let ranges = inverseBgByGroupId[groupId];
            let invertedRanges = invertRanges(ranges, framingRange);
            for (let invertedRange of invertedRanges) {
                let def = defByGroupId[groupId];
                let ui = eventUis[def.defId];
                bgRanges.push({
                    def,
                    ui,
                    instance: null,
                    range: invertedRange,
                    isStart: false,
                    isEnd: false,
                });
            }
        }
        for (let defId in inverseBgByDefId) {
            let ranges = inverseBgByDefId[defId];
            let invertedRanges = invertRanges(ranges, framingRange);
            for (let invertedRange of invertedRanges) {
                bgRanges.push({
                    def: eventStore.defs[defId],
                    ui: eventUis[defId],
                    instance: null,
                    range: invertedRange,
                    isStart: false,
                    isEnd: false,
                });
            }
        }
        return { bg: bgRanges, fg: fgRanges };
    }
    function hasBgRendering(def) {
        return def.ui.display === 'background' || def.ui.display === 'inverse-background';
    }
    function setElSeg(el, seg) {
        el.fcSeg = seg;
    }
    function getElSeg(el) {
        return el.fcSeg ||
            el.parentNode.fcSeg || // for the harness
            null;
    }
    // event ui computation
    function compileEventUis(eventDefs, eventUiBases) {
        return mapHash(eventDefs, (eventDef) => compileEventUi(eventDef, eventUiBases));
    }
    function compileEventUi(eventDef, eventUiBases) {
        let uis = [];
        if (eventUiBases['']) {
            uis.push(eventUiBases['']);
        }
        if (eventUiBases[eventDef.defId]) {
            uis.push(eventUiBases[eventDef.defId]);
        }
        uis.push(eventDef.ui);
        return combineEventUis(uis);
    }
    function sortEventSegs(segs, eventOrderSpecs) {
        let objs = segs.map(buildSegCompareObj);
        objs.sort((obj0, obj1) => compareByFieldSpecs(obj0, obj1, eventOrderSpecs));
        return objs.map((c) => c._seg);
    }
    // returns a object with all primitive props that can be compared
    function buildSegCompareObj(seg) {
        let { eventRange } = seg;
        let eventDef = eventRange.def;
        let range = eventRange.instance ? eventRange.instance.range : eventRange.range;
        let start = range.start ? range.start.valueOf() : 0; // TODO: better support for open-range events
        let end = range.end ? range.end.valueOf() : 0; // "
        return Object.assign(Object.assign(Object.assign({}, eventDef.extendedProps), eventDef), { id: eventDef.publicId, start,
            end, duration: end - start, allDay: Number(eventDef.allDay), _seg: seg });
    }
    function computeSegDraggable(seg, context) {
        let { pluginHooks } = context;
        let transformers = pluginHooks.isDraggableTransformers;
        let { def, ui } = seg.eventRange;
        let val = ui.startEditable;
        for (let transformer of transformers) {
            val = transformer(val, def, ui, context);
        }
        return val;
    }
    function computeSegStartResizable(seg, context) {
        return seg.isStart && seg.eventRange.ui.durationEditable && context.options.eventResizableFromStart;
    }
    function computeSegEndResizable(seg, context) {
        return seg.isEnd && seg.eventRange.ui.durationEditable;
    }
    function buildSegTimeText(seg, timeFormat, context, defaultDisplayEventTime, // defaults to true
    defaultDisplayEventEnd, // defaults to true
    startOverride, endOverride) {
        let { dateEnv, options } = context;
        let { displayEventTime, displayEventEnd } = options;
        let eventDef = seg.eventRange.def;
        let eventInstance = seg.eventRange.instance;
        if (displayEventTime == null) {
            displayEventTime = defaultDisplayEventTime !== false;
        }
        if (displayEventEnd == null) {
            displayEventEnd = defaultDisplayEventEnd !== false;
        }
        let wholeEventStart = eventInstance.range.start;
        let wholeEventEnd = eventInstance.range.end;
        let segStart = startOverride || seg.start || seg.eventRange.range.start;
        let segEnd = endOverride || seg.end || seg.eventRange.range.end;
        let isStartDay = startOfDay(wholeEventStart).valueOf() === startOfDay(segStart).valueOf();
        let isEndDay = startOfDay(addMs(wholeEventEnd, -1)).valueOf() === startOfDay(addMs(segEnd, -1)).valueOf();
        if (displayEventTime && !eventDef.allDay && (isStartDay || isEndDay)) {
            segStart = isStartDay ? wholeEventStart : segStart;
            segEnd = isEndDay ? wholeEventEnd : segEnd;
            if (displayEventEnd && eventDef.hasEnd) {
                return dateEnv.formatRange(segStart, segEnd, timeFormat, {
                    forcedStartTzo: startOverride ? null : eventInstance.forcedStartTzo,
                    forcedEndTzo: endOverride ? null : eventInstance.forcedEndTzo,
                });
            }
            return dateEnv.format(segStart, timeFormat, {
                forcedTzo: startOverride ? null : eventInstance.forcedStartTzo, // nooooo, same
            });
        }
        return '';
    }
    function getSegMeta(seg, todayRange, nowDate) {
        let segRange = seg.eventRange.range;
        return {
            isPast: segRange.end <= (nowDate || todayRange.start),
            isFuture: segRange.start >= (nowDate || todayRange.end),
            isToday: todayRange && rangeContainsMarker(todayRange, segRange.start),
        };
    }
    function getEventClassNames(props) {
        let classNames = ['fc-event'];
        if (props.isMirror) {
            classNames.push('fc-event-mirror');
        }
        if (props.isDraggable) {
            classNames.push('fc-event-draggable');
        }
        if (props.isStartResizable || props.isEndResizable) {
            classNames.push('fc-event-resizable');
        }
        if (props.isDragging) {
            classNames.push('fc-event-dragging');
        }
        if (props.isResizing) {
            classNames.push('fc-event-resizing');
        }
        if (props.isSelected) {
            classNames.push('fc-event-selected');
        }
        if (props.isStart) {
            classNames.push('fc-event-start');
        }
        if (props.isEnd) {
            classNames.push('fc-event-end');
        }
        if (props.isPast) {
            classNames.push('fc-event-past');
        }
        if (props.isToday) {
            classNames.push('fc-event-today');
        }
        if (props.isFuture) {
            classNames.push('fc-event-future');
        }
        return classNames;
    }
    function buildEventRangeKey(eventRange) {
        return eventRange.instance
            ? eventRange.instance.instanceId
            : `${eventRange.def.defId}:${eventRange.range.start.toISOString()}`;
        // inverse-background events don't have specific instances. TODO: better solution
    }
    function getSegAnchorAttrs(seg, context) {
        let { def, instance } = seg.eventRange;
        let { url } = def;
        if (url) {
            return { href: url };
        }
        let { emitter, options } = context;
        let { eventInteractive } = options;
        if (eventInteractive == null) {
            eventInteractive = def.interactive;
            if (eventInteractive == null) {
                eventInteractive = Boolean(emitter.hasHandlers('eventClick'));
            }
        }
        // mock what happens in EventClicking
        if (eventInteractive) {
            // only attach keyboard-related handlers because click handler is already done in EventClicking
            return createAriaKeyboardAttrs((ev) => {
                emitter.trigger('eventClick', {
                    el: ev.target,
                    event: new EventImpl(context, def, instance),
                    jsEvent: ev,
                    view: context.viewApi,
                });
            });
        }
        return {};
    }

    const STANDARD_PROPS = {
        start: identity,
        end: identity,
        allDay: Boolean,
    };
    function parseDateSpan(raw, dateEnv, defaultDuration) {
        let span = parseOpenDateSpan(raw, dateEnv);
        let { range } = span;
        if (!range.start) {
            return null;
        }
        if (!range.end) {
            if (defaultDuration == null) {
                return null;
            }
            range.end = dateEnv.add(range.start, defaultDuration);
        }
        return span;
    }
    /*
    TODO: somehow combine with parseRange?
    Will return null if the start/end props were present but parsed invalidly.
    */
    function parseOpenDateSpan(raw, dateEnv) {
        let { refined: standardProps, extra } = refineProps(raw, STANDARD_PROPS);
        let startMeta = standardProps.start ? dateEnv.createMarkerMeta(standardProps.start) : null;
        let endMeta = standardProps.end ? dateEnv.createMarkerMeta(standardProps.end) : null;
        let { allDay } = standardProps;
        if (allDay == null) {
            allDay = (startMeta && startMeta.isTimeUnspecified) &&
                (!endMeta || endMeta.isTimeUnspecified);
        }
        return Object.assign({ range: {
                start: startMeta ? startMeta.marker : null,
                end: endMeta ? endMeta.marker : null,
            }, allDay }, extra);
    }
    function isDateSpansEqual(span0, span1) {
        return rangesEqual(span0.range, span1.range) &&
            span0.allDay === span1.allDay &&
            isSpanPropsEqual(span0, span1);
    }
    // the NON-DATE-RELATED props
    function isSpanPropsEqual(span0, span1) {
        for (let propName in span1) {
            if (propName !== 'range' && propName !== 'allDay') {
                if (span0[propName] !== span1[propName]) {
                    return false;
                }
            }
        }
        // are there any props that span0 has that span1 DOESN'T have?
        // both have range/allDay, so no need to special-case.
        for (let propName in span0) {
            if (!(propName in span1)) {
                return false;
            }
        }
        return true;
    }
    function buildDateSpanApi(span, dateEnv) {
        return Object.assign(Object.assign({}, buildRangeApi(span.range, dateEnv, span.allDay)), { allDay: span.allDay });
    }
    function buildRangeApiWithTimeZone(range, dateEnv, omitTime) {
        return Object.assign(Object.assign({}, buildRangeApi(range, dateEnv, omitTime)), { timeZone: dateEnv.timeZone });
    }
    function buildRangeApi(range, dateEnv, omitTime) {
        return {
            start: dateEnv.toDate(range.start),
            end: dateEnv.toDate(range.end),
            startStr: dateEnv.formatIso(range.start, { omitTime }),
            endStr: dateEnv.formatIso(range.end, { omitTime }),
        };
    }
    function fabricateEventRange(dateSpan, eventUiBases, context) {
        let res = refineEventDef({ editable: false }, context);
        let def = parseEventDef(res.refined, res.extra, '', // sourceId
        dateSpan.allDay, true, // hasEnd
        context);
        return {
            def,
            ui: compileEventUi(def, eventUiBases),
            instance: createEventInstance(def.defId, dateSpan.range),
            range: dateSpan.range,
            isStart: true,
            isEnd: true,
        };
    }

    let calendarSystemClassMap = {};
    function registerCalendarSystem(name, theClass) {
        calendarSystemClassMap[name] = theClass;
    }
    function createCalendarSystem(name) {
        return new calendarSystemClassMap[name]();
    }
    class GregorianCalendarSystem {
        getMarkerYear(d) {
            return d.getUTCFullYear();
        }
        getMarkerMonth(d) {
            return d.getUTCMonth();
        }
        getMarkerDay(d) {
            return d.getUTCDate();
        }
        arrayToMarker(arr) {
            return arrayToUtcDate(arr);
        }
        markerToArray(marker) {
            return dateToUtcArray(marker);
        }
    }
    registerCalendarSystem('gregory', GregorianCalendarSystem);

    const ISO_RE = /^\s*(\d{4})(-?(\d{2})(-?(\d{2})([T ](\d{2}):?(\d{2})(:?(\d{2})(\.(\d+))?)?(Z|(([-+])(\d{2})(:?(\d{2}))?))?)?)?)?$/;
    function parse(str) {
        let m = ISO_RE.exec(str);
        if (m) {
            let marker = new Date(Date.UTC(Number(m[1]), m[3] ? Number(m[3]) - 1 : 0, Number(m[5] || 1), Number(m[7] || 0), Number(m[8] || 0), Number(m[10] || 0), m[12] ? Number(`0.${m[12]}`) * 1000 : 0));
            if (isValidDate(marker)) {
                let timeZoneOffset = null;
                if (m[13]) {
                    timeZoneOffset = (m[15] === '-' ? -1 : 1) * (Number(m[16] || 0) * 60 +
                        Number(m[18] || 0));
                }
                return {
                    marker,
                    isTimeUnspecified: !m[6],
                    timeZoneOffset,
                };
            }
        }
        return null;
    }

    class DateEnv {
        constructor(settings) {
            let timeZone = this.timeZone = settings.timeZone;
            let isNamedTimeZone = timeZone !== 'local' && timeZone !== 'UTC';
            if (settings.namedTimeZoneImpl && isNamedTimeZone) {
                this.namedTimeZoneImpl = new settings.namedTimeZoneImpl(timeZone);
            }
            this.canComputeOffset = Boolean(!isNamedTimeZone || this.namedTimeZoneImpl);
            this.calendarSystem = createCalendarSystem(settings.calendarSystem);
            this.locale = settings.locale;
            this.weekDow = settings.locale.week.dow;
            this.weekDoy = settings.locale.week.doy;
            if (settings.weekNumberCalculation === 'ISO') {
                this.weekDow = 1;
                this.weekDoy = 4;
            }
            if (typeof settings.firstDay === 'number') {
                this.weekDow = settings.firstDay;
            }
            if (typeof settings.weekNumberCalculation === 'function') {
                this.weekNumberFunc = settings.weekNumberCalculation;
            }
            this.weekText = settings.weekText != null ? settings.weekText : settings.locale.options.weekText;
            this.weekTextLong = (settings.weekTextLong != null ? settings.weekTextLong : settings.locale.options.weekTextLong) || this.weekText;
            this.cmdFormatter = settings.cmdFormatter;
            this.defaultSeparator = settings.defaultSeparator;
        }
        // Creating / Parsing
        createMarker(input) {
            let meta = this.createMarkerMeta(input);
            if (meta === null) {
                return null;
            }
            return meta.marker;
        }
        createNowMarker() {
            if (this.canComputeOffset) {
                return this.timestampToMarker(new Date().valueOf());
            }
            // if we can't compute the current date val for a timezone,
            // better to give the current local date vals than UTC
            return arrayToUtcDate(dateToLocalArray(new Date()));
        }
        createMarkerMeta(input) {
            if (typeof input === 'string') {
                return this.parse(input);
            }
            let marker = null;
            if (typeof input === 'number') {
                marker = this.timestampToMarker(input);
            }
            else if (input instanceof Date) {
                input = input.valueOf();
                if (!isNaN(input)) {
                    marker = this.timestampToMarker(input);
                }
            }
            else if (Array.isArray(input)) {
                marker = arrayToUtcDate(input);
            }
            if (marker === null || !isValidDate(marker)) {
                return null;
            }
            return { marker, isTimeUnspecified: false, forcedTzo: null };
        }
        parse(s) {
            let parts = parse(s);
            if (parts === null) {
                return null;
            }
            let { marker } = parts;
            let forcedTzo = null;
            if (parts.timeZoneOffset !== null) {
                if (this.canComputeOffset) {
                    marker = this.timestampToMarker(marker.valueOf() - parts.timeZoneOffset * 60 * 1000);
                }
                else {
                    forcedTzo = parts.timeZoneOffset;
                }
            }
            return { marker, isTimeUnspecified: parts.isTimeUnspecified, forcedTzo };
        }
        // Accessors
        getYear(marker) {
            return this.calendarSystem.getMarkerYear(marker);
        }
        getMonth(marker) {
            return this.calendarSystem.getMarkerMonth(marker);
        }
        getDay(marker) {
            return this.calendarSystem.getMarkerDay(marker);
        }
        // Adding / Subtracting
        add(marker, dur) {
            let a = this.calendarSystem.markerToArray(marker);
            a[0] += dur.years;
            a[1] += dur.months;
            a[2] += dur.days;
            a[6] += dur.milliseconds;
            return this.calendarSystem.arrayToMarker(a);
        }
        subtract(marker, dur) {
            let a = this.calendarSystem.markerToArray(marker);
            a[0] -= dur.years;
            a[1] -= dur.months;
            a[2] -= dur.days;
            a[6] -= dur.milliseconds;
            return this.calendarSystem.arrayToMarker(a);
        }
        addYears(marker, n) {
            let a = this.calendarSystem.markerToArray(marker);
            a[0] += n;
            return this.calendarSystem.arrayToMarker(a);
        }
        addMonths(marker, n) {
            let a = this.calendarSystem.markerToArray(marker);
            a[1] += n;
            return this.calendarSystem.arrayToMarker(a);
        }
        // Diffing Whole Units
        diffWholeYears(m0, m1) {
            let { calendarSystem } = this;
            if (timeAsMs(m0) === timeAsMs(m1) &&
                calendarSystem.getMarkerDay(m0) === calendarSystem.getMarkerDay(m1) &&
                calendarSystem.getMarkerMonth(m0) === calendarSystem.getMarkerMonth(m1)) {
                return calendarSystem.getMarkerYear(m1) - calendarSystem.getMarkerYear(m0);
            }
            return null;
        }
        diffWholeMonths(m0, m1) {
            let { calendarSystem } = this;
            if (timeAsMs(m0) === timeAsMs(m1) &&
                calendarSystem.getMarkerDay(m0) === calendarSystem.getMarkerDay(m1)) {
                return (calendarSystem.getMarkerMonth(m1) - calendarSystem.getMarkerMonth(m0)) +
                    (calendarSystem.getMarkerYear(m1) - calendarSystem.getMarkerYear(m0)) * 12;
            }
            return null;
        }
        // Range / Duration
        greatestWholeUnit(m0, m1) {
            let n = this.diffWholeYears(m0, m1);
            if (n !== null) {
                return { unit: 'year', value: n };
            }
            n = this.diffWholeMonths(m0, m1);
            if (n !== null) {
                return { unit: 'month', value: n };
            }
            n = diffWholeWeeks(m0, m1);
            if (n !== null) {
                return { unit: 'week', value: n };
            }
            n = diffWholeDays(m0, m1);
            if (n !== null) {
                return { unit: 'day', value: n };
            }
            n = diffHours(m0, m1);
            if (isInt(n)) {
                return { unit: 'hour', value: n };
            }
            n = diffMinutes(m0, m1);
            if (isInt(n)) {
                return { unit: 'minute', value: n };
            }
            n = diffSeconds(m0, m1);
            if (isInt(n)) {
                return { unit: 'second', value: n };
            }
            return { unit: 'millisecond', value: m1.valueOf() - m0.valueOf() };
        }
        countDurationsBetween(m0, m1, d) {
            // TODO: can use greatestWholeUnit
            let diff;
            if (d.years) {
                diff = this.diffWholeYears(m0, m1);
                if (diff !== null) {
                    return diff / asRoughYears(d);
                }
            }
            if (d.months) {
                diff = this.diffWholeMonths(m0, m1);
                if (diff !== null) {
                    return diff / asRoughMonths(d);
                }
            }
            if (d.days) {
                diff = diffWholeDays(m0, m1);
                if (diff !== null) {
                    return diff / asRoughDays(d);
                }
            }
            return (m1.valueOf() - m0.valueOf()) / asRoughMs(d);
        }
        // Start-Of
        // these DON'T return zoned-dates. only UTC start-of dates
        startOf(m, unit) {
            if (unit === 'year') {
                return this.startOfYear(m);
            }
            if (unit === 'month') {
                return this.startOfMonth(m);
            }
            if (unit === 'week') {
                return this.startOfWeek(m);
            }
            if (unit === 'day') {
                return startOfDay(m);
            }
            if (unit === 'hour') {
                return startOfHour(m);
            }
            if (unit === 'minute') {
                return startOfMinute(m);
            }
            if (unit === 'second') {
                return startOfSecond(m);
            }
            return null;
        }
        startOfYear(m) {
            return this.calendarSystem.arrayToMarker([
                this.calendarSystem.getMarkerYear(m),
            ]);
        }
        startOfMonth(m) {
            return this.calendarSystem.arrayToMarker([
                this.calendarSystem.getMarkerYear(m),
                this.calendarSystem.getMarkerMonth(m),
            ]);
        }
        startOfWeek(m) {
            return this.calendarSystem.arrayToMarker([
                this.calendarSystem.getMarkerYear(m),
                this.calendarSystem.getMarkerMonth(m),
                m.getUTCDate() - ((m.getUTCDay() - this.weekDow + 7) % 7),
            ]);
        }
        // Week Number
        computeWeekNumber(marker) {
            if (this.weekNumberFunc) {
                return this.weekNumberFunc(this.toDate(marker));
            }
            return weekOfYear(marker, this.weekDow, this.weekDoy);
        }
        // TODO: choke on timeZoneName: long
        format(marker, formatter, dateOptions = {}) {
            return formatter.format({
                marker,
                timeZoneOffset: dateOptions.forcedTzo != null ?
                    dateOptions.forcedTzo :
                    this.offsetForMarker(marker),
            }, this);
        }
        formatRange(start, end, formatter, dateOptions = {}) {
            if (dateOptions.isEndExclusive) {
                end = addMs(end, -1);
            }
            return formatter.formatRange({
                marker: start,
                timeZoneOffset: dateOptions.forcedStartTzo != null ?
                    dateOptions.forcedStartTzo :
                    this.offsetForMarker(start),
            }, {
                marker: end,
                timeZoneOffset: dateOptions.forcedEndTzo != null ?
                    dateOptions.forcedEndTzo :
                    this.offsetForMarker(end),
            }, this, dateOptions.defaultSeparator);
        }
        /*
        DUMB: the omitTime arg is dumb. if we omit the time, we want to omit the timezone offset. and if we do that,
        might as well use buildIsoString or some other util directly
        */
        formatIso(marker, extraOptions = {}) {
            let timeZoneOffset = null;
            if (!extraOptions.omitTimeZoneOffset) {
                if (extraOptions.forcedTzo != null) {
                    timeZoneOffset = extraOptions.forcedTzo;
                }
                else {
                    timeZoneOffset = this.offsetForMarker(marker);
                }
            }
            return buildIsoString(marker, timeZoneOffset, extraOptions.omitTime);
        }
        // TimeZone
        timestampToMarker(ms) {
            if (this.timeZone === 'local') {
                return arrayToUtcDate(dateToLocalArray(new Date(ms)));
            }
            if (this.timeZone === 'UTC' || !this.namedTimeZoneImpl) {
                return new Date(ms);
            }
            return arrayToUtcDate(this.namedTimeZoneImpl.timestampToArray(ms));
        }
        offsetForMarker(m) {
            if (this.timeZone === 'local') {
                return -arrayToLocalDate(dateToUtcArray(m)).getTimezoneOffset(); // convert "inverse" offset to "normal" offset
            }
            if (this.timeZone === 'UTC') {
                return 0;
            }
            if (this.namedTimeZoneImpl) {
                return this.namedTimeZoneImpl.offsetForArray(dateToUtcArray(m));
            }
            return null;
        }
        // Conversion
        toDate(m, forcedTzo) {
            if (this.timeZone === 'local') {
                return arrayToLocalDate(dateToUtcArray(m));
            }
            if (this.timeZone === 'UTC') {
                return new Date(m.valueOf()); // make sure it's a copy
            }
            if (!this.namedTimeZoneImpl) {
                return new Date(m.valueOf() - (forcedTzo || 0));
            }
            return new Date(m.valueOf() -
                this.namedTimeZoneImpl.offsetForArray(dateToUtcArray(m)) * 1000 * 60);
        }
    }

    class NamedTimeZoneImpl {
        constructor(timeZoneName) {
            this.timeZoneName = timeZoneName;
        }
    }

    class SegHierarchy {
        constructor(getEntryThickness = (entry) => {
            // if no thickness known, assume 1 (if 0, so small it always fits)
            return entry.thickness || 1;
        }) {
            this.getEntryThickness = getEntryThickness;
            // settings
            this.strictOrder = false;
            this.allowReslicing = false;
            this.maxCoord = -1; // -1 means no max
            this.maxStackCnt = -1; // -1 means no max
            this.levelCoords = []; // ordered
            this.entriesByLevel = []; // parallel with levelCoords
            this.stackCnts = {}; // TODO: use better technique!?
        }
        addSegs(inputs) {
            let hiddenEntries = [];
            for (let input of inputs) {
                this.insertEntry(input, hiddenEntries);
            }
            return hiddenEntries;
        }
        insertEntry(entry, hiddenEntries) {
            let insertion = this.findInsertion(entry);
            if (this.isInsertionValid(insertion, entry)) {
                this.insertEntryAt(entry, insertion);
            }
            else {
                this.handleInvalidInsertion(insertion, entry, hiddenEntries);
            }
        }
        isInsertionValid(insertion, entry) {
            return (this.maxCoord === -1 || insertion.levelCoord + this.getEntryThickness(entry) <= this.maxCoord) &&
                (this.maxStackCnt === -1 || insertion.stackCnt < this.maxStackCnt);
        }
        handleInvalidInsertion(insertion, entry, hiddenEntries) {
            if (this.allowReslicing && insertion.touchingEntry) {
                const hiddenEntry = Object.assign(Object.assign({}, entry), { span: intersectSpans(entry.span, insertion.touchingEntry.span) });
                hiddenEntries.push(hiddenEntry);
                this.splitEntry(entry, insertion.touchingEntry, hiddenEntries);
            }
            else {
                hiddenEntries.push(entry);
            }
        }
        /*
        Does NOT add what hit the `barrier` into hiddenEntries. Should already be done.
        */
        splitEntry(entry, barrier, hiddenEntries) {
            let entrySpan = entry.span;
            let barrierSpan = barrier.span;
            if (entrySpan.start < barrierSpan.start) {
                this.insertEntry({
                    index: entry.index,
                    thickness: entry.thickness,
                    span: { start: entrySpan.start, end: barrierSpan.start },
                }, hiddenEntries);
            }
            if (entrySpan.end > barrierSpan.end) {
                this.insertEntry({
                    index: entry.index,
                    thickness: entry.thickness,
                    span: { start: barrierSpan.end, end: entrySpan.end },
                }, hiddenEntries);
            }
        }
        insertEntryAt(entry, insertion) {
            let { entriesByLevel, levelCoords } = this;
            if (insertion.lateral === -1) {
                // create a new level
                insertAt(levelCoords, insertion.level, insertion.levelCoord);
                insertAt(entriesByLevel, insertion.level, [entry]);
            }
            else {
                // insert into existing level
                insertAt(entriesByLevel[insertion.level], insertion.lateral, entry);
            }
            this.stackCnts[buildEntryKey(entry)] = insertion.stackCnt;
        }
        /*
        does not care about limits
        */
        findInsertion(newEntry) {
            let { levelCoords, entriesByLevel, strictOrder, stackCnts } = this;
            let levelCnt = levelCoords.length;
            let candidateCoord = 0;
            let touchingLevel = -1;
            let touchingLateral = -1;
            let touchingEntry = null;
            let stackCnt = 0;
            for (let trackingLevel = 0; trackingLevel < levelCnt; trackingLevel += 1) {
                const trackingCoord = levelCoords[trackingLevel];
                // if the current level is past the placed entry, we have found a good empty space and can stop.
                // if strictOrder, keep finding more lateral intersections.
                if (!strictOrder && trackingCoord >= candidateCoord + this.getEntryThickness(newEntry)) {
                    break;
                }
                let trackingEntries = entriesByLevel[trackingLevel];
                let trackingEntry;
                let searchRes = binarySearch(trackingEntries, newEntry.span.start, getEntrySpanEnd); // find first entry after newEntry's end
                let lateralIndex = searchRes[0] + searchRes[1]; // if exact match (which doesn't collide), go to next one
                while ( // loop through entries that horizontally intersect
                (trackingEntry = trackingEntries[lateralIndex]) && // but not past the whole entry list
                    trackingEntry.span.start < newEntry.span.end // and not entirely past newEntry
                ) {
                    let trackingEntryBottom = trackingCoord + this.getEntryThickness(trackingEntry);
                    // intersects into the top of the candidate?
                    if (trackingEntryBottom > candidateCoord) {
                        candidateCoord = trackingEntryBottom;
                        touchingEntry = trackingEntry;
                        touchingLevel = trackingLevel;
                        touchingLateral = lateralIndex;
                    }
                    // butts up against top of candidate? (will happen if just intersected as well)
                    if (trackingEntryBottom === candidateCoord) {
                        // accumulate the highest possible stackCnt of the trackingEntries that butt up
                        stackCnt = Math.max(stackCnt, stackCnts[buildEntryKey(trackingEntry)] + 1);
                    }
                    lateralIndex += 1;
                }
            }
            // the destination level will be after touchingEntry's level. find it
            let destLevel = 0;
            if (touchingEntry) {
                destLevel = touchingLevel + 1;
                while (destLevel < levelCnt && levelCoords[destLevel] < candidateCoord) {
                    destLevel += 1;
                }
            }
            // if adding to an existing level, find where to insert
            let destLateral = -1;
            if (destLevel < levelCnt && levelCoords[destLevel] === candidateCoord) {
                destLateral = binarySearch(entriesByLevel[destLevel], newEntry.span.end, getEntrySpanEnd)[0];
            }
            return {
                touchingLevel,
                touchingLateral,
                touchingEntry,
                stackCnt,
                levelCoord: candidateCoord,
                level: destLevel,
                lateral: destLateral,
            };
        }
        // sorted by levelCoord (lowest to highest)
        toRects() {
            let { entriesByLevel, levelCoords } = this;
            let levelCnt = entriesByLevel.length;
            let rects = [];
            for (let level = 0; level < levelCnt; level += 1) {
                let entries = entriesByLevel[level];
                let levelCoord = levelCoords[level];
                for (let entry of entries) {
                    rects.push(Object.assign(Object.assign({}, entry), { thickness: this.getEntryThickness(entry), levelCoord }));
                }
            }
            return rects;
        }
    }
    function getEntrySpanEnd(entry) {
        return entry.span.end;
    }
    function buildEntryKey(entry) {
        return entry.index + ':' + entry.span.start;
    }
    // returns groups with entries sorted by input order
    function groupIntersectingEntries(entries) {
        let merges = [];
        for (let entry of entries) {
            let filteredMerges = [];
            let hungryMerge = {
                span: entry.span,
                entries: [entry],
            };
            for (let merge of merges) {
                if (intersectSpans(merge.span, hungryMerge.span)) {
                    hungryMerge = {
                        entries: merge.entries.concat(hungryMerge.entries),
                        span: joinSpans(merge.span, hungryMerge.span),
                    };
                }
                else {
                    filteredMerges.push(merge);
                }
            }
            filteredMerges.push(hungryMerge);
            merges = filteredMerges;
        }
        return merges;
    }
    function joinSpans(span0, span1) {
        return {
            start: Math.min(span0.start, span1.start),
            end: Math.max(span0.end, span1.end),
        };
    }
    function intersectSpans(span0, span1) {
        let start = Math.max(span0.start, span1.start);
        let end = Math.min(span0.end, span1.end);
        if (start < end) {
            return { start, end };
        }
        return null;
    }
    // general util
    // ---------------------------------------------------------------------------------------------------------------------
    function insertAt(arr, index, item) {
        arr.splice(index, 0, item);
    }
    function binarySearch(a, searchVal, getItemVal) {
        let startIndex = 0;
        let endIndex = a.length; // exclusive
        if (!endIndex || searchVal < getItemVal(a[startIndex])) { // no items OR before first item
            return [0, 0];
        }
        if (searchVal > getItemVal(a[endIndex - 1])) { // after last item
            return [endIndex, 0];
        }
        while (startIndex < endIndex) {
            let middleIndex = Math.floor(startIndex + (endIndex - startIndex) / 2);
            let middleVal = getItemVal(a[middleIndex]);
            if (searchVal < middleVal) {
                endIndex = middleIndex;
            }
            else if (searchVal > middleVal) {
                startIndex = middleIndex + 1;
            }
            else { // equal!
                return [middleIndex, 1];
            }
        }
        return [startIndex, 0];
    }

    class Interaction {
        constructor(settings) {
            this.component = settings.component;
            this.isHitComboAllowed = settings.isHitComboAllowed || null;
        }
        destroy() {
        }
    }
    function parseInteractionSettings(component, input) {
        return {
            component,
            el: input.el,
            useEventCenter: input.useEventCenter != null ? input.useEventCenter : true,
            isHitComboAllowed: input.isHitComboAllowed || null,
        };
    }
    function interactionSettingsToStore(settings) {
        return {
            [settings.component.uid]: settings,
        };
    }
    // global state
    const interactionSettingsStore = {};

    /*
    An abstraction for a dragging interaction originating on an event.
    Does higher-level things than PointerDragger, such as possibly:
    - a "mirror" that moves with the pointer
    - a minimum number of pixels or other criteria for a true drag to begin

    subclasses must emit:
    - pointerdown
    - dragstart
    - dragmove
    - pointerup
    - dragend
    */
    class ElementDragging {
        constructor(el, selector) {
            this.emitter = new Emitter();
        }
        destroy() {
        }
        setMirrorIsVisible(bool) {
            // optional if subclass doesn't want to support a mirror
        }
        setMirrorNeedsRevert(bool) {
            // optional if subclass doesn't want to support a mirror
        }
        setAutoScrollEnabled(bool) {
            // optional
        }
    }

    // TODO: get rid of this in favor of options system,
    // tho it's really easy to access this globally rather than pass thru options.
    const config = {};

    /*
    Information about what will happen when an external element is dragged-and-dropped
    onto a calendar. Contains information for creating an event.
    */
    const DRAG_META_REFINERS = {
        startTime: createDuration,
        duration: createDuration,
        create: Boolean,
        sourceId: String,
    };
    function parseDragMeta(raw) {
        let { refined, extra } = refineProps(raw, DRAG_META_REFINERS);
        return {
            startTime: refined.startTime || null,
            duration: refined.duration || null,
            create: refined.create != null ? refined.create : true,
            sourceId: refined.sourceId,
            leftoverProps: extra,
        };
    }

    class CalendarRoot extends BaseComponent {
        constructor() {
            super(...arguments);
            this.state = {
                forPrint: false,
            };
            this.handleBeforePrint = () => {
                flushSync(() => {
                    this.setState({ forPrint: true });
                });
            };
            this.handleAfterPrint = () => {
                flushSync(() => {
                    this.setState({ forPrint: false });
                });
            };
        }
        render() {
            let { props } = this;
            let { options } = props;
            let { forPrint } = this.state;
            let isHeightAuto = forPrint || options.height === 'auto' || options.contentHeight === 'auto';
            let height = (!isHeightAuto && options.height != null) ? options.height : '';
            let classNames = [
                'fc',
                forPrint ? 'fc-media-print' : 'fc-media-screen',
                `fc-direction-${options.direction}`,
                props.theme.getClass('root'),
            ];
            if (!getCanVGrowWithinCell()) {
                classNames.push('fc-liquid-hack');
            }
            return props.children(classNames, height, isHeightAuto, forPrint);
        }
        componentDidMount() {
            let { emitter } = this.props;
            emitter.on('_beforeprint', this.handleBeforePrint);
            emitter.on('_afterprint', this.handleAfterPrint);
        }
        componentWillUnmount() {
            let { emitter } = this.props;
            emitter.off('_beforeprint', this.handleBeforePrint);
            emitter.off('_afterprint', this.handleAfterPrint);
        }
    }

    // Computes a default column header formatting string if `colFormat` is not explicitly defined
    function computeFallbackHeaderFormat(datesRepDistinctDays, dayCnt) {
        // if more than one week row, or if there are a lot of columns with not much space,
        // put just the day numbers will be in each cell
        if (!datesRepDistinctDays || dayCnt > 10) {
            return createFormatter({ weekday: 'short' }); // "Sat"
        }
        if (dayCnt > 1) {
            return createFormatter({ weekday: 'short', month: 'numeric', day: 'numeric', omitCommas: true }); // "Sat 11/12"
        }
        return createFormatter({ weekday: 'long' }); // "Saturday"
    }

    const CLASS_NAME = 'fc-col-header-cell'; // do the cushion too? no
    function renderInner$1(renderProps) {
        return renderProps.text;
    }

    class ContentInjector extends BaseComponent {
        constructor() {
            super(...arguments);
            this.id = guid();
            this.queuedDomNodes = [];
            this.currentDomNodes = [];
            this.handleEl = (el) => {
                const { options } = this.context;
                const { generatorName } = this.props;
                if (!options.customRenderingReplaces || !hasCustomRenderingHandler(generatorName, options)) {
                    this.updateElRef(el);
                }
            };
            this.updateElRef = (el) => {
                if (this.props.elRef) {
                    setRef(this.props.elRef, el);
                }
            };
        }
        render() {
            const { props, context } = this;
            const { options } = context;
            const { customGenerator, defaultGenerator, renderProps } = props;
            const attrs = buildElAttrs(props, [], this.handleEl);
            let useDefault = false;
            let innerContent;
            let queuedDomNodes = [];
            let currentGeneratorMeta;
            if (customGenerator != null) {
                const customGeneratorRes = typeof customGenerator === 'function' ?
                    customGenerator(renderProps, y) :
                    customGenerator;
                if (customGeneratorRes === true) {
                    useDefault = true;
                }
                else {
                    const isObject = customGeneratorRes && typeof customGeneratorRes === 'object'; // non-null
                    if (isObject && ('html' in customGeneratorRes)) {
                        attrs.dangerouslySetInnerHTML = { __html: customGeneratorRes.html };
                    }
                    else if (isObject && ('domNodes' in customGeneratorRes)) {
                        queuedDomNodes = Array.prototype.slice.call(customGeneratorRes.domNodes);
                    }
                    else if (isObject
                        ? i$1(customGeneratorRes) // vdom node
                        : typeof customGeneratorRes !== 'function' // primitive value (like string or number)
                    ) {
                        // use in vdom
                        innerContent = customGeneratorRes;
                    }
                    else {
                        // an exotic object for handleCustomRendering
                        currentGeneratorMeta = customGeneratorRes;
                    }
                }
            }
            else {
                useDefault = !hasCustomRenderingHandler(props.generatorName, options);
            }
            if (useDefault && defaultGenerator) {
                innerContent = defaultGenerator(renderProps);
            }
            this.queuedDomNodes = queuedDomNodes;
            this.currentGeneratorMeta = currentGeneratorMeta;
            return y(props.elTag, attrs, innerContent);
        }
        componentDidMount() {
            this.applyQueueudDomNodes();
            this.triggerCustomRendering(true);
        }
        componentDidUpdate() {
            this.applyQueueudDomNodes();
            this.triggerCustomRendering(true);
        }
        componentWillUnmount() {
            this.triggerCustomRendering(false); // TODO: different API for removal?
        }
        triggerCustomRendering(isActive) {
            var _a;
            const { props, context } = this;
            const { handleCustomRendering, customRenderingMetaMap } = context.options;
            if (handleCustomRendering) {
                const generatorMeta = (_a = this.currentGeneratorMeta) !== null && _a !== void 0 ? _a : customRenderingMetaMap === null || customRenderingMetaMap === void 0 ? void 0 : customRenderingMetaMap[props.generatorName];
                if (generatorMeta) {
                    handleCustomRendering(Object.assign(Object.assign({ id: this.id, isActive, containerEl: this.base, reportNewContainerEl: this.updateElRef, // front-end framework tells us about new container els
                        generatorMeta }, props), { elClasses: (props.elClasses || []).filter(isTruthy) }));
                }
            }
        }
        applyQueueudDomNodes() {
            const { queuedDomNodes, currentDomNodes } = this;
            const el = this.base;
            if (!isArraysEqual(queuedDomNodes, currentDomNodes)) {
                currentDomNodes.forEach(removeElement);
                for (let newNode of queuedDomNodes) {
                    el.appendChild(newNode);
                }
                this.currentDomNodes = queuedDomNodes;
            }
        }
    }
    ContentInjector.addPropsEquality({
        elClasses: isArraysEqual,
        elStyle: isPropsEqual,
        elAttrs: isNonHandlerPropsEqual,
        renderProps: isPropsEqual,
    });
    // Util
    /*
    Does UI-framework provide custom way of rendering that does not use Preact VDOM
    AND does the calendar's options define custom rendering?
    AKA. Should we NOT render the default content?
    */
    function hasCustomRenderingHandler(generatorName, options) {
        var _a;
        return Boolean(options.handleCustomRendering &&
            generatorName &&
            ((_a = options.customRenderingMetaMap) === null || _a === void 0 ? void 0 : _a[generatorName]));
    }
    function buildElAttrs(props, extraClassNames, elRef) {
        const attrs = Object.assign(Object.assign({}, props.elAttrs), { ref: elRef });
        if (props.elClasses || extraClassNames) {
            attrs.className = (props.elClasses || [])
                .concat(extraClassNames || [])
                .concat(attrs.className || [])
                .filter(Boolean)
                .join(' ');
        }
        if (props.elStyle) {
            attrs.style = props.elStyle;
        }
        return attrs;
    }
    function isTruthy(val) {
        return Boolean(val);
    }

    const RenderId = createContext(0);

    class ContentContainer extends x$1 {
        constructor() {
            super(...arguments);
            this.InnerContent = InnerContentInjector.bind(undefined, this);
            this.handleEl = (el) => {
                this.el = el;
                if (this.props.elRef) {
                    setRef(this.props.elRef, el);
                    if (el && this.didMountMisfire) {
                        this.componentDidMount();
                    }
                }
            };
        }
        render() {
            const { props } = this;
            const generatedClassNames = generateClassNames(props.classNameGenerator, props.renderProps);
            if (props.children) {
                const elAttrs = buildElAttrs(props, generatedClassNames, this.handleEl);
                const children = props.children(this.InnerContent, props.renderProps, elAttrs);
                if (props.elTag) {
                    return y(props.elTag, elAttrs, children);
                }
                else {
                    return children;
                }
            }
            else {
                return y((ContentInjector), Object.assign(Object.assign({}, props), { elRef: this.handleEl, elTag: props.elTag || 'div', elClasses: (props.elClasses || []).concat(generatedClassNames), renderId: this.context }));
            }
        }
        componentDidMount() {
            var _a, _b;
            if (this.el) {
                (_b = (_a = this.props).didMount) === null || _b === void 0 ? void 0 : _b.call(_a, Object.assign(Object.assign({}, this.props.renderProps), { el: this.el }));
            }
            else {
                this.didMountMisfire = true;
            }
        }
        componentWillUnmount() {
            var _a, _b;
            (_b = (_a = this.props).willUnmount) === null || _b === void 0 ? void 0 : _b.call(_a, Object.assign(Object.assign({}, this.props.renderProps), { el: this.el }));
        }
    }
    ContentContainer.contextType = RenderId;
    function InnerContentInjector(containerComponent, props) {
        const parentProps = containerComponent.props;
        return y((ContentInjector), Object.assign({ renderProps: parentProps.renderProps, generatorName: parentProps.generatorName, customGenerator: parentProps.customGenerator, defaultGenerator: parentProps.defaultGenerator, renderId: containerComponent.context }, props));
    }
    // Utils
    function generateClassNames(classNameGenerator, renderProps) {
        const classNames = typeof classNameGenerator === 'function' ?
            classNameGenerator(renderProps) :
            classNameGenerator || [];
        return typeof classNames === 'string' ? [classNames] : classNames;
    }

    // BAD name for this class now. used in the Header
    class TableDateCell extends BaseComponent {
        render() {
            let { dateEnv, options, theme, viewApi } = this.context;
            let { props } = this;
            let { date, dateProfile } = props;
            let dayMeta = getDateMeta(date, props.todayRange, null, dateProfile);
            let classNames = [CLASS_NAME].concat(getDayClassNames(dayMeta, theme));
            let text = dateEnv.format(date, props.dayHeaderFormat);
            // if colCnt is 1, we are already in a day-view and don't need a navlink
            let navLinkAttrs = (!dayMeta.isDisabled && props.colCnt > 1)
                ? buildNavLinkAttrs(this.context, date)
                : {};
            let publicDate = dateEnv.toDate(date);
            // workaround for Luxon (and maybe moment) returning prior-days when start-of-day
            // in DST gap: https://github.com/fullcalendar/fullcalendar/issues/7633
            if (dateEnv.namedTimeZoneImpl) {
                publicDate = addMs(publicDate, 3600000); // add an hour
            }
            let renderProps = Object.assign(Object.assign(Object.assign({ date: publicDate, view: viewApi }, props.extraRenderProps), { text }), dayMeta);
            return (y(ContentContainer, { elTag: "th", elClasses: classNames, elAttrs: Object.assign({ role: 'columnheader', colSpan: props.colSpan, 'data-date': !dayMeta.isDisabled ? formatDayString(date) : undefined }, props.extraDataAttrs), renderProps: renderProps, generatorName: "dayHeaderContent", customGenerator: options.dayHeaderContent, defaultGenerator: renderInner$1, classNameGenerator: options.dayHeaderClassNames, didMount: options.dayHeaderDidMount, willUnmount: options.dayHeaderWillUnmount }, (InnerContainer) => (y("div", { className: "fc-scrollgrid-sync-inner" }, !dayMeta.isDisabled && (y(InnerContainer, { elTag: "a", elAttrs: navLinkAttrs, elClasses: [
                    'fc-col-header-cell-cushion',
                    props.isSticky && 'fc-sticky',
                ] }))))));
        }
    }

    const WEEKDAY_FORMAT = createFormatter({ weekday: 'long' });
    class TableDowCell extends BaseComponent {
        render() {
            let { props } = this;
            let { dateEnv, theme, viewApi, options } = this.context;
            let date = addDays(new Date(259200000), props.dow); // start with Sun, 04 Jan 1970 00:00:00 GMT
            let dateMeta = {
                dow: props.dow,
                isDisabled: false,
                isFuture: false,
                isPast: false,
                isToday: false,
                isOther: false,
            };
            let text = dateEnv.format(date, props.dayHeaderFormat);
            let renderProps = Object.assign(Object.assign(Object.assign(Object.assign({ // TODO: make this public?
                date }, dateMeta), { view: viewApi }), props.extraRenderProps), { text });
            return (y(ContentContainer, { elTag: "th", elClasses: [
                    CLASS_NAME,
                    ...getDayClassNames(dateMeta, theme),
                    ...(props.extraClassNames || []),
                ], elAttrs: Object.assign({ role: 'columnheader', colSpan: props.colSpan }, props.extraDataAttrs), renderProps: renderProps, generatorName: "dayHeaderContent", customGenerator: options.dayHeaderContent, defaultGenerator: renderInner$1, classNameGenerator: options.dayHeaderClassNames, didMount: options.dayHeaderDidMount, willUnmount: options.dayHeaderWillUnmount }, (InnerContent) => (y("div", { className: "fc-scrollgrid-sync-inner" },
                y(InnerContent, { elTag: "a", elClasses: [
                        'fc-col-header-cell-cushion',
                        props.isSticky && 'fc-sticky',
                    ], elAttrs: {
                        'aria-label': dateEnv.format(date, WEEKDAY_FORMAT),
                    } })))));
        }
    }

    class NowTimer extends x$1 {
        constructor(props, context) {
            super(props, context);
            this.handleRefresh = () => {
                let timing = this.computeTiming();
                if (timing.state.nowDate.valueOf() !== this.state.nowDate.valueOf()) {
                    this.setState(timing.state);
                }
                this.clearTimeout();
                this.setTimeout(timing.waitMs);
            };
            this.handleVisibilityChange = () => {
                if (!document.hidden) {
                    this.handleRefresh();
                }
            };
            this.state = this.computeTiming().state;
        }
        render() {
            let { props, state } = this;
            return props.children(state.nowDate, state.todayRange);
        }
        componentDidMount() {
            this.setTimeout();
            this.context.nowManager.addResetListener(this.handleRefresh);
            // fired tab becomes visible after being hidden
            document.addEventListener('visibilitychange', this.handleVisibilityChange);
        }
        componentDidUpdate(prevProps) {
            if (prevProps.unit !== this.props.unit) {
                this.clearTimeout();
                this.setTimeout();
            }
        }
        componentWillUnmount() {
            this.clearTimeout();
            this.context.nowManager.removeResetListener(this.handleRefresh);
            document.removeEventListener('visibilitychange', this.handleVisibilityChange);
        }
        computeTiming() {
            let { props, context } = this;
            let unroundedNow = context.nowManager.getDateMarker();
            let { nowIndicatorSnap } = context.options;
            if (nowIndicatorSnap === 'auto') {
                nowIndicatorSnap =
                    // large unit?
                    /year|month|week|day/.test(props.unit) ||
                        // if slotDuration 30 mins for example, would NOT appear to snap (legacy behavior)
                        (props.unitValue || 1) === 1;
            }
            let nowDate;
            let waitMs;
            if (nowIndicatorSnap) {
                nowDate = context.dateEnv.startOf(unroundedNow, props.unit); // aka currentUnitStart
                let nextUnitStart = context.dateEnv.add(nowDate, createDuration(1, props.unit));
                waitMs = nextUnitStart.valueOf() - unroundedNow.valueOf();
            }
            else {
                nowDate = unroundedNow;
                waitMs = 1000 * 60; // 1 minute
            }
            // there is a max setTimeout ms value (https://stackoverflow.com/a/3468650/96342)
            // ensure no longer than a day
            waitMs = Math.min(1000 * 60 * 60 * 24, waitMs);
            return {
                state: { nowDate, todayRange: buildDayRange(nowDate) },
                waitMs,
            };
        }
        setTimeout(waitMs = this.computeTiming().waitMs) {
            // NOTE: timeout could take longer than expected if tab sleeps,
            // which is why we listen to 'visibilitychange'
            this.timeoutId = setTimeout(() => {
                // NOTE: timeout could also return *earlier* than expected, and we need to wait 2 ms more
                // This is why use use same waitMs from computeTiming, so we don't skip an interval while
                // .setState() is executing
                const timing = this.computeTiming();
                this.setState(timing.state, () => {
                    this.setTimeout(timing.waitMs);
                });
            }, waitMs);
        }
        clearTimeout() {
            if (this.timeoutId) {
                clearTimeout(this.timeoutId);
            }
        }
    }
    NowTimer.contextType = ViewContextType;
    function buildDayRange(date) {
        let start = startOfDay(date);
        let end = addDays(start, 1);
        return { start, end };
    }

    class DayHeader extends BaseComponent {
        constructor() {
            super(...arguments);
            this.createDayHeaderFormatter = memoize(createDayHeaderFormatter);
        }
        render() {
            let { context } = this;
            let { dates, dateProfile, datesRepDistinctDays, renderIntro } = this.props;
            let dayHeaderFormat = this.createDayHeaderFormatter(context.options.dayHeaderFormat, datesRepDistinctDays, dates.length);
            return (y(NowTimer, { unit: "day" }, (nowDate, todayRange) => (y("tr", { role: "row" },
                renderIntro && renderIntro('day'),
                dates.map((date) => (datesRepDistinctDays ? (y(TableDateCell, { key: date.toISOString(), date: date, dateProfile: dateProfile, todayRange: todayRange, colCnt: dates.length, dayHeaderFormat: dayHeaderFormat })) : (y(TableDowCell, { key: date.getUTCDay(), dow: date.getUTCDay(), dayHeaderFormat: dayHeaderFormat }))))))));
        }
    }
    function createDayHeaderFormatter(explicitFormat, datesRepDistinctDays, dateCnt) {
        return explicitFormat || computeFallbackHeaderFormat(datesRepDistinctDays, dateCnt);
    }

    class DaySeriesModel {
        constructor(range, dateProfileGenerator) {
            let date = range.start;
            let { end } = range;
            let indices = [];
            let dates = [];
            let dayIndex = -1;
            while (date < end) { // loop each day from start to end
                if (dateProfileGenerator.isHiddenDay(date)) {
                    indices.push(dayIndex + 0.5); // mark that it's between indices
                }
                else {
                    dayIndex += 1;
                    indices.push(dayIndex);
                    dates.push(date);
                }
                date = addDays(date, 1);
            }
            this.dates = dates;
            this.indices = indices;
            this.cnt = dates.length;
        }
        sliceRange(range) {
            let firstIndex = this.getDateDayIndex(range.start); // inclusive first index
            let lastIndex = this.getDateDayIndex(addDays(range.end, -1)); // inclusive last index
            let clippedFirstIndex = Math.max(0, firstIndex);
            let clippedLastIndex = Math.min(this.cnt - 1, lastIndex);
            // deal with in-between indices
            clippedFirstIndex = Math.ceil(clippedFirstIndex); // in-between starts round to next cell
            clippedLastIndex = Math.floor(clippedLastIndex); // in-between ends round to prev cell
            if (clippedFirstIndex <= clippedLastIndex) {
                return {
                    firstIndex: clippedFirstIndex,
                    lastIndex: clippedLastIndex,
                    isStart: firstIndex === clippedFirstIndex,
                    isEnd: lastIndex === clippedLastIndex,
                };
            }
            return null;
        }
        // Given a date, returns its chronolocial cell-index from the first cell of the grid.
        // If the date lies between cells (because of hiddenDays), returns a floating-point value between offsets.
        // If before the first offset, returns a negative number.
        // If after the last offset, returns an offset past the last cell offset.
        // Only works for *start* dates of cells. Will not work for exclusive end dates for cells.
        getDateDayIndex(date) {
            let { indices } = this;
            let dayOffset = Math.floor(diffDays(this.dates[0], date));
            if (dayOffset < 0) {
                return indices[0] - 1;
            }
            if (dayOffset >= indices.length) {
                return indices[indices.length - 1] + 1;
            }
            return indices[dayOffset];
        }
    }

    class DayTableModel {
        constructor(daySeries, breakOnWeeks) {
            let { dates } = daySeries;
            let daysPerRow;
            let firstDay;
            let rowCnt;
            if (breakOnWeeks) {
                // count columns until the day-of-week repeats
                firstDay = dates[0].getUTCDay();
                for (daysPerRow = 1; daysPerRow < dates.length; daysPerRow += 1) {
                    if (dates[daysPerRow].getUTCDay() === firstDay) {
                        break;
                    }
                }
                rowCnt = Math.ceil(dates.length / daysPerRow);
            }
            else {
                rowCnt = 1;
                daysPerRow = dates.length;
            }
            this.rowCnt = rowCnt;
            this.colCnt = daysPerRow;
            this.daySeries = daySeries;
            this.cells = this.buildCells();
            this.headerDates = this.buildHeaderDates();
        }
        buildCells() {
            let rows = [];
            for (let row = 0; row < this.rowCnt; row += 1) {
                let cells = [];
                for (let col = 0; col < this.colCnt; col += 1) {
                    cells.push(this.buildCell(row, col));
                }
                rows.push(cells);
            }
            return rows;
        }
        buildCell(row, col) {
            let date = this.daySeries.dates[row * this.colCnt + col];
            return {
                key: date.toISOString(),
                date,
            };
        }
        buildHeaderDates() {
            let dates = [];
            for (let col = 0; col < this.colCnt; col += 1) {
                dates.push(this.cells[0][col].date);
            }
            return dates;
        }
        sliceRange(range) {
            let { colCnt } = this;
            let seriesSeg = this.daySeries.sliceRange(range);
            let segs = [];
            if (seriesSeg) {
                let { firstIndex, lastIndex } = seriesSeg;
                let index = firstIndex;
                while (index <= lastIndex) {
                    let row = Math.floor(index / colCnt);
                    let nextIndex = Math.min((row + 1) * colCnt, lastIndex + 1);
                    segs.push({
                        row,
                        firstCol: index % colCnt,
                        lastCol: (nextIndex - 1) % colCnt,
                        isStart: seriesSeg.isStart && index === firstIndex,
                        isEnd: seriesSeg.isEnd && (nextIndex - 1) === lastIndex,
                    });
                    index = nextIndex;
                }
            }
            return segs;
        }
    }

    class Slicer {
        constructor() {
            this.sliceBusinessHours = memoize(this._sliceBusinessHours);
            this.sliceDateSelection = memoize(this._sliceDateSpan);
            this.sliceEventStore = memoize(this._sliceEventStore);
            this.sliceEventDrag = memoize(this._sliceInteraction);
            this.sliceEventResize = memoize(this._sliceInteraction);
            this.forceDayIfListItem = false; // hack
        }
        sliceProps(props, dateProfile, nextDayThreshold, context, ...extraArgs) {
            let { eventUiBases } = props;
            let eventSegs = this.sliceEventStore(props.eventStore, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs);
            return {
                dateSelectionSegs: this.sliceDateSelection(props.dateSelection, dateProfile, nextDayThreshold, eventUiBases, context, ...extraArgs),
                businessHourSegs: this.sliceBusinessHours(props.businessHours, dateProfile, nextDayThreshold, context, ...extraArgs),
                fgEventSegs: eventSegs.fg,
                bgEventSegs: eventSegs.bg,
                eventDrag: this.sliceEventDrag(props.eventDrag, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs),
                eventResize: this.sliceEventResize(props.eventResize, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs),
                eventSelection: props.eventSelection,
            }; // TODO: give interactionSegs?
        }
        sliceNowDate(// does not memoize
        date, dateProfile, nextDayThreshold, context, ...extraArgs) {
            return this._sliceDateSpan({ range: { start: date, end: addMs(date, 1) }, allDay: false }, // add 1 ms, protect against null range
            dateProfile, nextDayThreshold, {}, context, ...extraArgs);
        }
        _sliceBusinessHours(businessHours, dateProfile, nextDayThreshold, context, ...extraArgs) {
            if (!businessHours) {
                return [];
            }
            return this._sliceEventStore(expandRecurring(businessHours, computeActiveRange(dateProfile, Boolean(nextDayThreshold)), context), {}, dateProfile, nextDayThreshold, ...extraArgs).bg;
        }
        _sliceEventStore(eventStore, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs) {
            if (eventStore) {
                let rangeRes = sliceEventStore(eventStore, eventUiBases, computeActiveRange(dateProfile, Boolean(nextDayThreshold)), nextDayThreshold);
                return {
                    bg: this.sliceEventRanges(rangeRes.bg, extraArgs),
                    fg: this.sliceEventRanges(rangeRes.fg, extraArgs),
                };
            }
            return { bg: [], fg: [] };
        }
        _sliceInteraction(interaction, eventUiBases, dateProfile, nextDayThreshold, ...extraArgs) {
            if (!interaction) {
                return null;
            }
            let rangeRes = sliceEventStore(interaction.mutatedEvents, eventUiBases, computeActiveRange(dateProfile, Boolean(nextDayThreshold)), nextDayThreshold);
            return {
                segs: this.sliceEventRanges(rangeRes.fg, extraArgs),
                affectedInstances: interaction.affectedEvents.instances,
                isEvent: interaction.isEvent,
            };
        }
        _sliceDateSpan(dateSpan, dateProfile, nextDayThreshold, eventUiBases, context, ...extraArgs) {
            if (!dateSpan) {
                return [];
            }
            let activeRange = computeActiveRange(dateProfile, Boolean(nextDayThreshold));
            let activeDateSpanRange = intersectRanges(dateSpan.range, activeRange);
            if (activeDateSpanRange) {
                dateSpan = Object.assign(Object.assign({}, dateSpan), { range: activeDateSpanRange });
                let eventRange = fabricateEventRange(dateSpan, eventUiBases, context);
                let segs = this.sliceRange(dateSpan.range, ...extraArgs);
                for (let seg of segs) {
                    seg.eventRange = eventRange;
                }
                return segs;
            }
            return [];
        }
        /*
        "complete" seg means it has component and eventRange
        */
        sliceEventRanges(eventRanges, extraArgs) {
            let segs = [];
            for (let eventRange of eventRanges) {
                segs.push(...this.sliceEventRange(eventRange, extraArgs));
            }
            return segs;
        }
        /*
        "complete" seg means it has component and eventRange
        */
        sliceEventRange(eventRange, extraArgs) {
            let dateRange = eventRange.range;
            // hack to make multi-day events that are being force-displayed as list-items to take up only one day
            if (this.forceDayIfListItem && eventRange.ui.display === 'list-item') {
                dateRange = {
                    start: dateRange.start,
                    end: addDays(dateRange.start, 1),
                };
            }
            let segs = this.sliceRange(dateRange, ...extraArgs);
            for (let seg of segs) {
                seg.eventRange = eventRange;
                seg.isStart = eventRange.isStart && seg.isStart;
                seg.isEnd = eventRange.isEnd && seg.isEnd;
            }
            return segs;
        }
    }
    /*
    for incorporating slotMinTime/slotMaxTime if appropriate
    TODO: should be part of DateProfile!
    TimelineDateProfile already does this btw
    */
    function computeActiveRange(dateProfile, isComponentAllDay) {
        let range = dateProfile.activeRange;
        if (isComponentAllDay) {
            return range;
        }
        return {
            start: addMs(range.start, dateProfile.slotMinTime.milliseconds),
            end: addMs(range.end, dateProfile.slotMaxTime.milliseconds - 864e5), // 864e5 = ms in a day
        };
    }

    function reduceEventStore(eventStore, action, eventSources, dateProfile, context) {
        switch (action.type) {
            case 'RECEIVE_EVENTS': // raw
                return receiveRawEvents(eventStore, eventSources[action.sourceId], action.fetchId, action.fetchRange, action.rawEvents, context);
            case 'RESET_RAW_EVENTS':
                return resetRawEvents(eventStore, eventSources[action.sourceId], action.rawEvents, dateProfile.activeRange, context);
            case 'ADD_EVENTS': // already parsed, but not expanded
                return addEvent(eventStore, action.eventStore, // new ones
                dateProfile ? dateProfile.activeRange : null, context);
            case 'RESET_EVENTS':
                return action.eventStore;
            case 'MERGE_EVENTS': // already parsed and expanded
                return mergeEventStores(eventStore, action.eventStore);
            case 'PREV': // TODO: how do we track all actions that affect dateProfile :(
            case 'NEXT':
            case 'CHANGE_DATE':
            case 'CHANGE_VIEW_TYPE':
                if (dateProfile) {
                    return expandRecurring(eventStore, dateProfile.activeRange, context);
                }
                return eventStore;
            case 'REMOVE_EVENTS':
                return excludeSubEventStore(eventStore, action.eventStore);
            case 'REMOVE_EVENT_SOURCE':
                return excludeEventsBySourceId(eventStore, action.sourceId);
            case 'REMOVE_ALL_EVENT_SOURCES':
                return filterEventStoreDefs(eventStore, (eventDef) => (!eventDef.sourceId // only keep events with no source id
                ));
            case 'REMOVE_ALL_EVENTS':
                return createEmptyEventStore();
            default:
                return eventStore;
        }
    }
    function receiveRawEvents(eventStore, eventSource, fetchId, fetchRange, rawEvents, context) {
        if (eventSource && // not already removed
            fetchId === eventSource.latestFetchId // TODO: wish this logic was always in event-sources
        ) {
            let subset = parseEvents(transformRawEvents(rawEvents, eventSource, context), eventSource, context);
            if (fetchRange) {
                subset = expandRecurring(subset, fetchRange, context);
            }
            return mergeEventStores(excludeEventsBySourceId(eventStore, eventSource.sourceId), subset);
        }
        return eventStore;
    }
    function resetRawEvents(existingEventStore, eventSource, rawEvents, activeRange, context) {
        const { defIdMap, instanceIdMap } = buildPublicIdMaps(existingEventStore);
        let newEventStore = parseEvents(transformRawEvents(rawEvents, eventSource, context), eventSource, context, false, defIdMap, instanceIdMap);
        return expandRecurring(newEventStore, activeRange, context);
    }
    function transformRawEvents(rawEvents, eventSource, context) {
        let calEachTransform = context.options.eventDataTransform;
        let sourceEachTransform = eventSource ? eventSource.eventDataTransform : null;
        if (sourceEachTransform) {
            rawEvents = transformEachRawEvent(rawEvents, sourceEachTransform);
        }
        if (calEachTransform) {
            rawEvents = transformEachRawEvent(rawEvents, calEachTransform);
        }
        return rawEvents;
    }
    function transformEachRawEvent(rawEvents, func) {
        let refinedEvents;
        if (!func) {
            refinedEvents = rawEvents;
        }
        else {
            refinedEvents = [];
            for (let rawEvent of rawEvents) {
                let refinedEvent = func(rawEvent);
                if (refinedEvent) {
                    refinedEvents.push(refinedEvent);
                }
                else if (refinedEvent == null) {
                    refinedEvents.push(rawEvent);
                } // if a different falsy value, do nothing
            }
        }
        return refinedEvents;
    }
    function addEvent(eventStore, subset, expandRange, context) {
        if (expandRange) {
            subset = expandRecurring(subset, expandRange, context);
        }
        return mergeEventStores(eventStore, subset);
    }
    function rezoneEventStoreDates(eventStore, oldDateEnv, newDateEnv) {
        let { defs } = eventStore;
        let instances = mapHash(eventStore.instances, (instance) => {
            let def = defs[instance.defId];
            if (def.allDay) {
                return instance; // isn't dependent on timezone
            }
            return Object.assign(Object.assign({}, instance), { range: {
                    start: newDateEnv.createMarker(oldDateEnv.toDate(instance.range.start, instance.forcedStartTzo)),
                    end: newDateEnv.createMarker(oldDateEnv.toDate(instance.range.end, instance.forcedEndTzo)),
                }, forcedStartTzo: newDateEnv.canComputeOffset ? null : instance.forcedStartTzo, forcedEndTzo: newDateEnv.canComputeOffset ? null : instance.forcedEndTzo });
        });
        return { defs, instances };
    }
    function excludeEventsBySourceId(eventStore, sourceId) {
        return filterEventStoreDefs(eventStore, (eventDef) => eventDef.sourceId !== sourceId);
    }
    // QUESTION: why not just return instances? do a general object-property-exclusion util
    function excludeInstances(eventStore, removals) {
        return {
            defs: eventStore.defs,
            instances: filterHash(eventStore.instances, (instance) => !removals[instance.instanceId]),
        };
    }
    function buildPublicIdMaps(eventStore) {
        const { defs, instances } = eventStore;
        const defIdMap = {};
        const instanceIdMap = {};
        for (let defId in defs) {
            const def = defs[defId];
            const { publicId } = def;
            if (publicId) {
                defIdMap[publicId] = defId;
            }
        }
        for (let instanceId in instances) {
            const instance = instances[instanceId];
            const def = defs[instance.defId];
            const { publicId } = def;
            if (publicId) {
                instanceIdMap[publicId] = instanceId;
            }
        }
        return { defIdMap, instanceIdMap };
    }

    // high-level segmenting-aware tester functions
    // ------------------------------------------------------------------------------------------------------------------------
    function isInteractionValid(interaction, dateProfile, context) {
        let { instances } = interaction.mutatedEvents;
        for (let instanceId in instances) {
            if (!rangeContainsRange(dateProfile.validRange, instances[instanceId].range)) {
                return false;
            }
        }
        return isNewPropsValid({ eventDrag: interaction }, context); // HACK: the eventDrag props is used for ALL interactions
    }
    function isDateSelectionValid(dateSelection, dateProfile, context) {
        if (!rangeContainsRange(dateProfile.validRange, dateSelection.range)) {
            return false;
        }
        return isNewPropsValid({ dateSelection }, context);
    }
    function isNewPropsValid(newProps, context) {
        let calendarState = context.getCurrentData();
        let props = Object.assign({ businessHours: calendarState.businessHours, dateSelection: '', eventStore: calendarState.eventStore, eventUiBases: calendarState.eventUiBases, eventSelection: '', eventDrag: null, eventResize: null }, newProps);
        return (context.pluginHooks.isPropsValid || isPropsValid)(props, context);
    }
    function isPropsValid(state, context, dateSpanMeta = {}, filterConfig) {
        if (state.eventDrag && !isInteractionPropsValid(state, context, dateSpanMeta, filterConfig)) {
            return false;
        }
        if (state.dateSelection && !isDateSelectionPropsValid(state, context, dateSpanMeta, filterConfig)) {
            return false;
        }
        return true;
    }
    // Moving Event Validation
    // ------------------------------------------------------------------------------------------------------------------------
    function isInteractionPropsValid(state, context, dateSpanMeta, filterConfig) {
        let currentState = context.getCurrentData();
        let interaction = state.eventDrag; // HACK: the eventDrag props is used for ALL interactions
        let subjectEventStore = interaction.mutatedEvents;
        let subjectDefs = subjectEventStore.defs;
        let subjectInstances = subjectEventStore.instances;
        let subjectConfigs = compileEventUis(subjectDefs, interaction.isEvent ?
            state.eventUiBases :
            { '': currentState.selectionConfig });
        if (filterConfig) {
            subjectConfigs = mapHash(subjectConfigs, filterConfig);
        }
        // exclude the subject events. TODO: exclude defs too?
        let otherEventStore = excludeInstances(state.eventStore, interaction.affectedEvents.instances);
        let otherDefs = otherEventStore.defs;
        let otherInstances = otherEventStore.instances;
        let otherConfigs = compileEventUis(otherDefs, state.eventUiBases);
        for (let subjectInstanceId in subjectInstances) {
            let subjectInstance = subjectInstances[subjectInstanceId];
            let subjectRange = subjectInstance.range;
            let subjectConfig = subjectConfigs[subjectInstance.defId];
            let subjectDef = subjectDefs[subjectInstance.defId];
            // constraint
            if (!allConstraintsPass(subjectConfig.constraints, subjectRange, otherEventStore, state.businessHours, context)) {
                return false;
            }
            // overlap
            let { eventOverlap } = context.options;
            let eventOverlapFunc = typeof eventOverlap === 'function' ? eventOverlap : null;
            for (let otherInstanceId in otherInstances) {
                let otherInstance = otherInstances[otherInstanceId];
                // intersect! evaluate
                if (rangesIntersect(subjectRange, otherInstance.range)) {
                    let otherOverlap = otherConfigs[otherInstance.defId].overlap;
                    // consider the other event's overlap. only do this if the subject event is a "real" event
                    if (otherOverlap === false && interaction.isEvent) {
                        return false;
                    }
                    if (subjectConfig.overlap === false) {
                        return false;
                    }
                    if (eventOverlapFunc && !eventOverlapFunc(new EventImpl(context, otherDefs[otherInstance.defId], otherInstance), // still event
                    new EventImpl(context, subjectDef, subjectInstance))) {
                        return false;
                    }
                }
            }
            // allow (a function)
            let calendarEventStore = currentState.eventStore; // need global-to-calendar, not local to component (splittable)state
            for (let subjectAllow of subjectConfig.allows) {
                let subjectDateSpan = Object.assign(Object.assign({}, dateSpanMeta), { range: subjectInstance.range, allDay: subjectDef.allDay });
                let origDef = calendarEventStore.defs[subjectDef.defId];
                let origInstance = calendarEventStore.instances[subjectInstanceId];
                let eventApi;
                if (origDef) { // was previously in the calendar
                    eventApi = new EventImpl(context, origDef, origInstance);
                }
                else { // was an external event
                    eventApi = new EventImpl(context, subjectDef); // no instance, because had no dates
                }
                if (!subjectAllow(buildDateSpanApiWithContext(subjectDateSpan, context), eventApi)) {
                    return false;
                }
            }
        }
        return true;
    }
    // Date Selection Validation
    // ------------------------------------------------------------------------------------------------------------------------
    function isDateSelectionPropsValid(state, context, dateSpanMeta, filterConfig) {
        let relevantEventStore = state.eventStore;
        let relevantDefs = relevantEventStore.defs;
        let relevantInstances = relevantEventStore.instances;
        let selection = state.dateSelection;
        let selectionRange = selection.range;
        let { selectionConfig } = context.getCurrentData();
        if (filterConfig) {
            selectionConfig = filterConfig(selectionConfig);
        }
        // constraint
        if (!allConstraintsPass(selectionConfig.constraints, selectionRange, relevantEventStore, state.businessHours, context)) {
            return false;
        }
        // overlap
        let { selectOverlap } = context.options;
        let selectOverlapFunc = typeof selectOverlap === 'function' ? selectOverlap : null;
        for (let relevantInstanceId in relevantInstances) {
            let relevantInstance = relevantInstances[relevantInstanceId];
            // intersect! evaluate
            if (rangesIntersect(selectionRange, relevantInstance.range)) {
                if (selectionConfig.overlap === false) {
                    return false;
                }
                if (selectOverlapFunc && !selectOverlapFunc(new EventImpl(context, relevantDefs[relevantInstance.defId], relevantInstance), null)) {
                    return false;
                }
            }
        }
        // allow (a function)
        for (let selectionAllow of selectionConfig.allows) {
            let fullDateSpan = Object.assign(Object.assign({}, dateSpanMeta), selection);
            if (!selectionAllow(buildDateSpanApiWithContext(fullDateSpan, context), null)) {
                return false;
            }
        }
        return true;
    }
    // Constraint Utils
    // ------------------------------------------------------------------------------------------------------------------------
    function allConstraintsPass(constraints, subjectRange, otherEventStore, businessHoursUnexpanded, context) {
        for (let constraint of constraints) {
            if (!anyRangesContainRange(constraintToRanges(constraint, subjectRange, otherEventStore, businessHoursUnexpanded, context), subjectRange)) {
                return false;
            }
        }
        return true;
    }
    function constraintToRanges(constraint, subjectRange, // for expanding a recurring constraint, or expanding business hours
    otherEventStore, // for if constraint is an even group ID
    businessHoursUnexpanded, // for if constraint is 'businessHours'
    context) {
        if (constraint === 'businessHours') {
            return eventStoreToRanges(expandRecurring(businessHoursUnexpanded, subjectRange, context));
        }
        if (typeof constraint === 'string') { // an group ID
            return eventStoreToRanges(filterEventStoreDefs(otherEventStore, (eventDef) => eventDef.groupId === constraint));
        }
        if (typeof constraint === 'object' && constraint) { // non-null object
            return eventStoreToRanges(expandRecurring(constraint, subjectRange, context));
        }
        return []; // if it's false
    }
    // TODO: move to event-store file?
    function eventStoreToRanges(eventStore) {
        let { instances } = eventStore;
        let ranges = [];
        for (let instanceId in instances) {
            ranges.push(instances[instanceId].range);
        }
        return ranges;
    }
    // TODO: move to geom file?
    function anyRangesContainRange(outerRanges, innerRange) {
        for (let outerRange of outerRanges) {
            if (rangeContainsRange(outerRange, innerRange)) {
                return true;
            }
        }
        return false;
    }

    class JsonRequestError extends Error {
        constructor(message, response) {
            super(message);
            this.response = response;
        }
    }
    function requestJson(method, url, params) {
        method = method.toUpperCase();
        const fetchOptions = {
            method,
        };
        if (method === 'GET') {
            url += (url.indexOf('?') === -1 ? '?' : '&') +
                new URLSearchParams(params);
        }
        else {
            fetchOptions.body = new URLSearchParams(params);
            fetchOptions.headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            };
        }
        return fetch(url, fetchOptions).then((fetchRes) => {
            if (fetchRes.ok) {
                return fetchRes.json().then((parsedResponse) => {
                    return [parsedResponse, fetchRes];
                }, () => {
                    throw new JsonRequestError('Failure parsing JSON', fetchRes);
                });
            }
            else {
                throw new JsonRequestError('Request failed', fetchRes);
            }
        });
    }

    class DelayedRunner {
        constructor(drainedOption) {
            this.drainedOption = drainedOption;
            this.isRunning = false;
            this.isDirty = false;
            this.pauseDepths = {};
            this.timeoutId = 0;
        }
        request(delay) {
            this.isDirty = true;
            if (!this.isPaused()) {
                this.clearTimeout();
                if (delay == null) {
                    this.tryDrain();
                }
                else {
                    this.timeoutId = setTimeout(// NOT OPTIMAL! TODO: look at debounce
                    this.tryDrain.bind(this), delay);
                }
            }
        }
        pause(scope = '') {
            let { pauseDepths } = this;
            pauseDepths[scope] = (pauseDepths[scope] || 0) + 1;
            this.clearTimeout();
        }
        resume(scope = '', force) {
            let { pauseDepths } = this;
            if (scope in pauseDepths) {
                if (force) {
                    delete pauseDepths[scope];
                }
                else {
                    pauseDepths[scope] -= 1;
                    let depth = pauseDepths[scope];
                    if (depth <= 0) {
                        delete pauseDepths[scope];
                    }
                }
                this.tryDrain();
            }
        }
        isPaused() {
            return Object.keys(this.pauseDepths).length;
        }
        tryDrain() {
            if (!this.isRunning && !this.isPaused()) {
                this.isRunning = true;
                while (this.isDirty) {
                    this.isDirty = false;
                    this.drained(); // might set isDirty to true again
                }
                this.isRunning = false;
            }
        }
        clear() {
            this.clearTimeout();
            this.isDirty = false;
            this.pauseDepths = {};
        }
        clearTimeout() {
            if (this.timeoutId) {
                clearTimeout(this.timeoutId);
                this.timeoutId = 0;
            }
        }
        drained() {
            if (this.drainedOption) {
                this.drainedOption();
            }
        }
    }

    const VISIBLE_HIDDEN_RE = /^(visible|hidden)$/;
    class Scroller extends BaseComponent {
        constructor() {
            super(...arguments);
            this.handleEl = (el) => {
                this.el = el;
                setRef(this.props.elRef, el);
            };
        }
        render() {
            let { props } = this;
            let { liquid, liquidIsAbsolute } = props;
            let isAbsolute = liquid && liquidIsAbsolute;
            let className = ['fc-scroller'];
            if (liquid) {
                if (liquidIsAbsolute) {
                    className.push('fc-scroller-liquid-absolute');
                }
                else {
                    className.push('fc-scroller-liquid');
                }
            }
            return (y("div", { ref: this.handleEl, className: className.join(' '), style: {
                    overflowX: props.overflowX,
                    overflowY: props.overflowY,
                    left: (isAbsolute && -(props.overcomeLeft || 0)) || '',
                    right: (isAbsolute && -(props.overcomeRight || 0)) || '',
                    bottom: (isAbsolute && -(props.overcomeBottom || 0)) || '',
                    marginLeft: (!isAbsolute && -(props.overcomeLeft || 0)) || '',
                    marginRight: (!isAbsolute && -(props.overcomeRight || 0)) || '',
                    marginBottom: (!isAbsolute && -(props.overcomeBottom || 0)) || '',
                    maxHeight: props.maxHeight || '',
                } }, props.children));
        }
        needsXScrolling() {
            if (VISIBLE_HIDDEN_RE.test(this.props.overflowX)) {
                return false;
            }
            // testing scrollWidth>clientWidth is unreliable cross-browser when pixel heights aren't integers.
            // much more reliable to see if children are taller than the scroller, even tho doesn't account for
            // inner-child margins and absolute positioning
            let { el } = this;
            let realClientWidth = this.el.getBoundingClientRect().width - this.getYScrollbarWidth();
            let { children } = el;
            for (let i = 0; i < children.length; i += 1) {
                let childEl = children[i];
                if (childEl.getBoundingClientRect().width > realClientWidth) {
                    return true;
                }
            }
            return false;
        }
        needsYScrolling() {
            if (VISIBLE_HIDDEN_RE.test(this.props.overflowY)) {
                return false;
            }
            // testing scrollHeight>clientHeight is unreliable cross-browser when pixel heights aren't integers.
            // much more reliable to see if children are taller than the scroller, even tho doesn't account for
            // inner-child margins and absolute positioning
            let { el } = this;
            let realClientHeight = this.el.getBoundingClientRect().height - this.getXScrollbarWidth();
            let { children } = el;
            for (let i = 0; i < children.length; i += 1) {
                let childEl = children[i];
                if (childEl.getBoundingClientRect().height > realClientHeight) {
                    return true;
                }
            }
            return false;
        }
        getXScrollbarWidth() {
            if (VISIBLE_HIDDEN_RE.test(this.props.overflowX)) {
                return 0;
            }
            return this.el.offsetHeight - this.el.clientHeight; // only works because we guarantee no borders. TODO: add to CSS with important?
        }
        getYScrollbarWidth() {
            if (VISIBLE_HIDDEN_RE.test(this.props.overflowY)) {
                return 0;
            }
            return this.el.offsetWidth - this.el.clientWidth; // only works because we guarantee no borders. TODO: add to CSS with important?
        }
    }

    /*
    TODO: somehow infer OtherArgs from masterCallback?
    TODO: infer RefType from masterCallback if provided
    */
    class RefMap {
        constructor(masterCallback) {
            this.masterCallback = masterCallback;
            this.currentMap = {};
            this.depths = {};
            this.callbackMap = {};
            this.handleValue = (val, key) => {
                let { depths, currentMap } = this;
                let removed = false;
                let added = false;
                if (val !== null) {
                    // for bug... ACTUALLY: can probably do away with this now that callers don't share numeric indices anymore
                    removed = (key in currentMap);
                    currentMap[key] = val;
                    depths[key] = (depths[key] || 0) + 1;
                    added = true;
                }
                else {
                    depths[key] -= 1;
                    if (!depths[key]) {
                        delete currentMap[key];
                        delete this.callbackMap[key];
                        removed = true;
                    }
                }
                if (this.masterCallback) {
                    if (removed) {
                        this.masterCallback(null, String(key));
                    }
                    if (added) {
                        this.masterCallback(val, String(key));
                    }
                }
            };
        }
        createRef(key) {
            let refCallback = this.callbackMap[key];
            if (!refCallback) {
                refCallback = this.callbackMap[key] = (val) => {
                    this.handleValue(val, String(key));
                };
            }
            return refCallback;
        }
        // TODO: check callers that don't care about order. should use getAll instead
        // NOTE: this method has become less valuable now that we are encouraged to map order by some other index
        // TODO: provide ONE array-export function, buildArray, which fails on non-numeric indexes. caller can manipulate and "collect"
        collect(startIndex, endIndex, step) {
            return collectFromHash(this.currentMap, startIndex, endIndex, step);
        }
        getAll() {
            return hashValuesToArray(this.currentMap);
        }
    }

    function computeShrinkWidth(chunkEls) {
        let shrinkCells = findElements(chunkEls, '.fc-scrollgrid-shrink');
        let largestWidth = 0;
        for (let shrinkCell of shrinkCells) {
            largestWidth = Math.max(largestWidth, computeSmallestCellWidth(shrinkCell));
        }
        return Math.ceil(largestWidth); // <table> elements work best with integers. round up to ensure contents fits
    }
    function getSectionHasLiquidHeight(props, sectionConfig) {
        return props.liquid && sectionConfig.liquid; // does the section do liquid-height? (need to have whole scrollgrid liquid-height as well)
    }
    function getAllowYScrolling(props, sectionConfig) {
        return sectionConfig.maxHeight != null || // if its possible for the height to max out, we might need scrollbars
            getSectionHasLiquidHeight(props, sectionConfig); // if the section is liquid height, it might condense enough to require scrollbars
    }
    // TODO: ONLY use `arg`. force out internal function to use same API
    function renderChunkContent(sectionConfig, chunkConfig, arg, isHeader) {
        let { expandRows } = arg;
        let content = typeof chunkConfig.content === 'function' ?
            chunkConfig.content(arg) :
            y('table', {
                role: 'presentation',
                className: [
                    chunkConfig.tableClassName,
                    sectionConfig.syncRowHeights ? 'fc-scrollgrid-sync-table' : '',
                ].join(' '),
                style: {
                    minWidth: arg.tableMinWidth,
                    width: arg.clientWidth,
                    height: expandRows ? arg.clientHeight : '', // css `height` on a <table> serves as a min-height
                },
            }, arg.tableColGroupNode, y(isHeader ? 'thead' : 'tbody', {
                role: 'presentation',
            }, typeof chunkConfig.rowContent === 'function'
                ? chunkConfig.rowContent(arg)
                : chunkConfig.rowContent));
        return content;
    }
    function isColPropsEqual(cols0, cols1) {
        return isArraysEqual(cols0, cols1, isPropsEqual);
    }
    function renderMicroColGroup(cols, shrinkWidth) {
        let colNodes = [];
        /*
        for ColProps with spans, it would have been great to make a single <col span="">
        HOWEVER, Chrome was getting messing up distributing the width to <td>/<th> elements with colspans.
        SOLUTION: making individual <col> elements makes Chrome behave.
        */
        for (let colProps of cols) {
            let span = colProps.span || 1;
            for (let i = 0; i < span; i += 1) {
                colNodes.push(y("col", { style: {
                        width: colProps.width === 'shrink' ? sanitizeShrinkWidth(shrinkWidth) : (colProps.width || ''),
                        minWidth: colProps.minWidth || '',
                    } }));
            }
        }
        return y('colgroup', {}, ...colNodes);
    }
    function sanitizeShrinkWidth(shrinkWidth) {
        /* why 4? if we do 0, it will kill any border, which are needed for computeSmallestCellWidth
        4 accounts for 2 2-pixel borders. TODO: better solution? */
        return shrinkWidth == null ? 4 : shrinkWidth;
    }
    function hasShrinkWidth(cols) {
        for (let col of cols) {
            if (col.width === 'shrink') {
                return true;
            }
        }
        return false;
    }
    function getScrollGridClassNames(liquid, context) {
        let classNames = [
            'fc-scrollgrid',
            context.theme.getClass('table'),
        ];
        if (liquid) {
            classNames.push('fc-scrollgrid-liquid');
        }
        return classNames;
    }
    function getSectionClassNames(sectionConfig, wholeTableVGrow) {
        let classNames = [
            'fc-scrollgrid-section',
            `fc-scrollgrid-section-${sectionConfig.type}`,
            sectionConfig.className, // used?
        ];
        if (wholeTableVGrow && sectionConfig.liquid && sectionConfig.maxHeight == null) {
            classNames.push('fc-scrollgrid-section-liquid');
        }
        if (sectionConfig.isSticky) {
            classNames.push('fc-scrollgrid-section-sticky');
        }
        return classNames;
    }
    function renderScrollShim(arg) {
        return (y("div", { className: "fc-scrollgrid-sticky-shim", style: {
                width: arg.clientWidth,
                minWidth: arg.tableMinWidth,
            } }));
    }
    function getStickyHeaderDates(options) {
        let { stickyHeaderDates } = options;
        if (stickyHeaderDates == null || stickyHeaderDates === 'auto') {
            stickyHeaderDates = options.height === 'auto' || options.viewHeight === 'auto';
        }
        return stickyHeaderDates;
    }
    function getStickyFooterScrollbar(options) {
        let { stickyFooterScrollbar } = options;
        if (stickyFooterScrollbar == null || stickyFooterScrollbar === 'auto') {
            stickyFooterScrollbar = options.height === 'auto' || options.viewHeight === 'auto';
        }
        return stickyFooterScrollbar;
    }

    class SimpleScrollGrid extends BaseComponent {
        constructor() {
            super(...arguments);
            this.processCols = memoize((a) => a, isColPropsEqual); // so we get same `cols` props every time
            // yucky to memoize VNodes, but much more efficient for consumers
            this.renderMicroColGroup = memoize(renderMicroColGroup);
            this.scrollerRefs = new RefMap();
            this.scrollerElRefs = new RefMap(this._handleScrollerEl.bind(this));
            this.state = {
                shrinkWidth: null,
                forceYScrollbars: false,
                scrollerClientWidths: {},
                scrollerClientHeights: {},
            };
            // TODO: can do a really simple print-view. dont need to join rows
            this.handleSizing = () => {
                this.safeSetState(Object.assign({ shrinkWidth: this.computeShrinkWidth() }, this.computeScrollerDims()));
            };
        }
        render() {
            let { props, state, context } = this;
            let sectionConfigs = props.sections || [];
            let cols = this.processCols(props.cols);
            let microColGroupNode = this.renderMicroColGroup(cols, state.shrinkWidth);
            let classNames = getScrollGridClassNames(props.liquid, context);
            if (props.collapsibleWidth) {
                classNames.push('fc-scrollgrid-collapsible');
            }
            // TODO: make DRY
            let configCnt = sectionConfigs.length;
            let configI = 0;
            let currentConfig;
            let headSectionNodes = [];
            let bodySectionNodes = [];
            let footSectionNodes = [];
            while (configI < configCnt && (currentConfig = sectionConfigs[configI]).type === 'header') {
                headSectionNodes.push(this.renderSection(currentConfig, microColGroupNode, true));
                configI += 1;
            }
            while (configI < configCnt && (currentConfig = sectionConfigs[configI]).type === 'body') {
                bodySectionNodes.push(this.renderSection(currentConfig, microColGroupNode, false));
                configI += 1;
            }
            while (configI < configCnt && (currentConfig = sectionConfigs[configI]).type === 'footer') {
                footSectionNodes.push(this.renderSection(currentConfig, microColGroupNode, true));
                configI += 1;
            }
            // firefox bug: when setting height on table and there is a thead or tfoot,
            // the necessary height:100% on the liquid-height body section forces the *whole* table to be taller. (bug #5524)
            // use getCanVGrowWithinCell as a way to detect table-stupid firefox.
            // if so, use a simpler dom structure, jam everything into a lone tbody.
            let isBuggy = !getCanVGrowWithinCell();
            const roleAttrs = { role: 'rowgroup' };
            return y('table', {
                role: 'grid',
                className: classNames.join(' '),
                style: { height: props.height },
            }, Boolean(!isBuggy && headSectionNodes.length) && y('thead', roleAttrs, ...headSectionNodes), Boolean(!isBuggy && bodySectionNodes.length) && y('tbody', roleAttrs, ...bodySectionNodes), Boolean(!isBuggy && footSectionNodes.length) && y('tfoot', roleAttrs, ...footSectionNodes), isBuggy && y('tbody', roleAttrs, ...headSectionNodes, ...bodySectionNodes, ...footSectionNodes));
        }
        renderSection(sectionConfig, microColGroupNode, isHeader) {
            if ('outerContent' in sectionConfig) {
                return (y(_, { key: sectionConfig.key }, sectionConfig.outerContent));
            }
            return (y("tr", { key: sectionConfig.key, role: "presentation", className: getSectionClassNames(sectionConfig, this.props.liquid).join(' ') }, this.renderChunkTd(sectionConfig, microColGroupNode, sectionConfig.chunk, isHeader)));
        }
        renderChunkTd(sectionConfig, microColGroupNode, chunkConfig, isHeader) {
            if ('outerContent' in chunkConfig) {
                return chunkConfig.outerContent;
            }
            let { props } = this;
            let { forceYScrollbars, scrollerClientWidths, scrollerClientHeights } = this.state;
            let needsYScrolling = getAllowYScrolling(props, sectionConfig); // TODO: do lazily. do in section config?
            let isLiquid = getSectionHasLiquidHeight(props, sectionConfig);
            // for `!props.liquid` - is WHOLE scrollgrid natural height?
            // TODO: do same thing in advanced scrollgrid? prolly not b/c always has horizontal scrollbars
            let overflowY = !props.liquid ? 'visible' :
                forceYScrollbars ? 'scroll' :
                    !needsYScrolling ? 'hidden' :
                        'auto';
            let sectionKey = sectionConfig.key;
            let content = renderChunkContent(sectionConfig, chunkConfig, {
                tableColGroupNode: microColGroupNode,
                tableMinWidth: '',
                clientWidth: (!props.collapsibleWidth && scrollerClientWidths[sectionKey] !== undefined) ? scrollerClientWidths[sectionKey] : null,
                clientHeight: scrollerClientHeights[sectionKey] !== undefined ? scrollerClientHeights[sectionKey] : null,
                expandRows: sectionConfig.expandRows,
                syncRowHeights: false,
                rowSyncHeights: [],
                reportRowHeightChange: () => { },
            }, isHeader);
            return y(isHeader ? 'th' : 'td', {
                ref: chunkConfig.elRef,
                role: 'presentation',
            }, y("div", { className: `fc-scroller-harness${isLiquid ? ' fc-scroller-harness-liquid' : ''}` },
                y(Scroller, { ref: this.scrollerRefs.createRef(sectionKey), elRef: this.scrollerElRefs.createRef(sectionKey), overflowY: overflowY, overflowX: !props.liquid ? 'visible' : 'hidden' /* natural height? */, maxHeight: sectionConfig.maxHeight, liquid: isLiquid, liquidIsAbsolute // because its within a harness
                    : true }, content)));
        }
        _handleScrollerEl(scrollerEl, key) {
            let section = getSectionByKey(this.props.sections, key);
            if (section) {
                setRef(section.chunk.scrollerElRef, scrollerEl);
            }
        }
        componentDidMount() {
            this.handleSizing();
            this.context.addResizeHandler(this.handleSizing);
        }
        componentDidUpdate() {
            // TODO: need better solution when state contains non-sizing things
            this.handleSizing();
        }
        componentWillUnmount() {
            this.context.removeResizeHandler(this.handleSizing);
        }
        computeShrinkWidth() {
            return hasShrinkWidth(this.props.cols)
                ? computeShrinkWidth(this.scrollerElRefs.getAll())
                : 0;
        }
        computeScrollerDims() {
            let scrollbarWidth = getScrollbarWidths();
            let { scrollerRefs, scrollerElRefs } = this;
            let forceYScrollbars = false;
            let scrollerClientWidths = {};
            let scrollerClientHeights = {};
            for (let sectionKey in scrollerRefs.currentMap) {
                let scroller = scrollerRefs.currentMap[sectionKey];
                if (scroller && scroller.needsYScrolling()) {
                    forceYScrollbars = true;
                    break;
                }
            }
            for (let section of this.props.sections) {
                let sectionKey = section.key;
                let scrollerEl = scrollerElRefs.currentMap[sectionKey];
                if (scrollerEl) {
                    let harnessEl = scrollerEl.parentNode; // TODO: weird way to get this. need harness b/c doesn't include table borders
                    scrollerClientWidths[sectionKey] = Math.floor(harnessEl.getBoundingClientRect().width - (forceYScrollbars
                        ? scrollbarWidth.y // use global because scroller might not have scrollbars yet but will need them in future
                        : 0));
                    scrollerClientHeights[sectionKey] = Math.floor(harnessEl.getBoundingClientRect().height);
                }
            }
            return { forceYScrollbars, scrollerClientWidths, scrollerClientHeights };
        }
    }
    SimpleScrollGrid.addStateEquality({
        scrollerClientWidths: isPropsEqual,
        scrollerClientHeights: isPropsEqual,
    });
    function getSectionByKey(sections, key) {
        for (let section of sections) {
            if (section.key === key) {
                return section;
            }
        }
        return null;
    }

    class EventContainer extends BaseComponent {
        constructor() {
            super(...arguments);
            // memo
            this.buildPublicEvent = memoize((context, eventDef, eventInstance) => new EventImpl(context, eventDef, eventInstance));
            this.handleEl = (el) => {
                this.el = el;
                setRef(this.props.elRef, el);
                if (el) {
                    setElSeg(el, this.props.seg);
                }
            };
        }
        render() {
            const { props, context } = this;
            const { options } = context;
            const { seg } = props;
            const { eventRange } = seg;
            const { ui } = eventRange;
            const renderProps = {
                event: this.buildPublicEvent(context, eventRange.def, eventRange.instance),
                view: context.viewApi,
                timeText: props.timeText,
                textColor: ui.textColor,
                backgroundColor: ui.backgroundColor,
                borderColor: ui.borderColor,
                isDraggable: !props.disableDragging && computeSegDraggable(seg, context),
                isStartResizable: !props.disableResizing && computeSegStartResizable(seg, context),
                isEndResizable: !props.disableResizing && computeSegEndResizable(seg),
                isMirror: Boolean(props.isDragging || props.isResizing || props.isDateSelecting),
                isStart: Boolean(seg.isStart),
                isEnd: Boolean(seg.isEnd),
                isPast: Boolean(props.isPast),
                isFuture: Boolean(props.isFuture),
                isToday: Boolean(props.isToday),
                isSelected: Boolean(props.isSelected),
                isDragging: Boolean(props.isDragging),
                isResizing: Boolean(props.isResizing),
            };
            return (y(ContentContainer, { elRef: this.handleEl, elTag: props.elTag, elAttrs: props.elAttrs, elClasses: [
                    ...getEventClassNames(renderProps),
                    ...seg.eventRange.ui.classNames,
                    ...(props.elClasses || []),
                ], elStyle: props.elStyle, renderProps: renderProps, generatorName: "eventContent", customGenerator: options.eventContent, defaultGenerator: props.defaultGenerator, classNameGenerator: options.eventClassNames, didMount: options.eventDidMount, willUnmount: options.eventWillUnmount }, props.children));
        }
        componentDidUpdate(prevProps) {
            if (this.el && this.props.seg !== prevProps.seg) {
                setElSeg(this.el, this.props.seg);
            }
        }
    }

    // should not be a purecomponent
    class StandardEvent extends BaseComponent {
        render() {
            let { props, context } = this;
            let { options } = context;
            let { seg } = props;
            let { ui } = seg.eventRange;
            let timeFormat = options.eventTimeFormat || props.defaultTimeFormat;
            let timeText = buildSegTimeText(seg, timeFormat, context, props.defaultDisplayEventTime, props.defaultDisplayEventEnd);
            return (y(EventContainer, Object.assign({}, props /* includes elRef */, { elTag: "a", elStyle: {
                    borderColor: ui.borderColor,
                    backgroundColor: ui.backgroundColor,
                }, elAttrs: getSegAnchorAttrs(seg, context), defaultGenerator: renderInnerContent$1, timeText: timeText }), (InnerContent, eventContentArg) => (y(_, null,
                y(InnerContent, { elTag: "div", elClasses: ['fc-event-main'], elStyle: { color: eventContentArg.textColor } }),
                Boolean(eventContentArg.isStartResizable) && (y("div", { className: "fc-event-resizer fc-event-resizer-start" })),
                Boolean(eventContentArg.isEndResizable) && (y("div", { className: "fc-event-resizer fc-event-resizer-end" }))))));
        }
    }
    StandardEvent.addPropsEquality({
        seg: isPropsEqual,
    });
    function renderInnerContent$1(innerProps) {
        return (y("div", { className: "fc-event-main-frame" },
            innerProps.timeText && (y("div", { className: "fc-event-time" }, innerProps.timeText)),
            y("div", { className: "fc-event-title-container" },
                y("div", { className: "fc-event-title fc-sticky" }, innerProps.event.title || y(_, null, "\u00A0")))));
    }

    const NowIndicatorContainer = (props) => (y(ViewContextType.Consumer, null, (context) => {
        let { options } = context;
        let renderProps = {
            isAxis: props.isAxis,
            date: context.dateEnv.toDate(props.date),
            view: context.viewApi,
        };
        return (y(ContentContainer, { elRef: props.elRef, elTag: props.elTag || 'div', elAttrs: props.elAttrs, elClasses: props.elClasses, elStyle: props.elStyle, renderProps: renderProps, generatorName: "nowIndicatorContent", customGenerator: options.nowIndicatorContent, classNameGenerator: options.nowIndicatorClassNames, didMount: options.nowIndicatorDidMount, willUnmount: options.nowIndicatorWillUnmount }, props.children));
    }));

    const DAY_NUM_FORMAT = createFormatter({ day: 'numeric' });
    class DayCellContainer extends BaseComponent {
        constructor() {
            super(...arguments);
            this.refineRenderProps = memoizeObjArg(refineRenderProps);
        }
        render() {
            let { props, context } = this;
            let { options } = context;
            let renderProps = this.refineRenderProps({
                date: props.date,
                dateProfile: props.dateProfile,
                todayRange: props.todayRange,
                isMonthStart: props.isMonthStart || false,
                showDayNumber: props.showDayNumber,
                extraRenderProps: props.extraRenderProps,
                viewApi: context.viewApi,
                dateEnv: context.dateEnv,
                monthStartFormat: options.monthStartFormat,
            });
            return (y(ContentContainer, { elRef: props.elRef, elTag: props.elTag, elAttrs: Object.assign(Object.assign({}, props.elAttrs), (renderProps.isDisabled ? {} : { 'data-date': formatDayString(props.date) })), elClasses: [
                    ...getDayClassNames(renderProps, context.theme),
                    ...(props.elClasses || []),
                ], elStyle: props.elStyle, renderProps: renderProps, generatorName: "dayCellContent", customGenerator: options.dayCellContent, defaultGenerator: props.defaultGenerator, classNameGenerator: 
                // don't use custom classNames if disabled
                renderProps.isDisabled ? undefined : options.dayCellClassNames, didMount: options.dayCellDidMount, willUnmount: options.dayCellWillUnmount }, props.children));
        }
    }
    function hasCustomDayCellContent(options) {
        return Boolean(options.dayCellContent || hasCustomRenderingHandler('dayCellContent', options));
    }
    function refineRenderProps(raw) {
        let { date, dateEnv, dateProfile, isMonthStart } = raw;
        let dayMeta = getDateMeta(date, raw.todayRange, null, dateProfile);
        let dayNumberText = raw.showDayNumber ? (dateEnv.format(date, isMonthStart ? raw.monthStartFormat : DAY_NUM_FORMAT)) : '';
        return Object.assign(Object.assign(Object.assign({ date: dateEnv.toDate(date), view: raw.viewApi }, dayMeta), { isMonthStart,
            dayNumberText }), raw.extraRenderProps);
    }

    class BgEvent extends BaseComponent {
        render() {
            let { props } = this;
            let { seg } = props;
            return (y(EventContainer, { elTag: "div", elClasses: ['fc-bg-event'], elStyle: { backgroundColor: seg.eventRange.ui.backgroundColor }, defaultGenerator: renderInnerContent, seg: seg, timeText: "", isDragging: false, isResizing: false, isDateSelecting: false, isSelected: false, isPast: props.isPast, isFuture: props.isFuture, isToday: props.isToday, disableDragging: true, disableResizing: true }));
        }
    }
    function renderInnerContent(props) {
        let { title } = props.event;
        return title && (y("div", { className: "fc-event-title" }, props.event.title));
    }
    function renderFill(fillType) {
        return (y("div", { className: `fc-${fillType}` }));
    }

    const WeekNumberContainer = (props) => (y(ViewContextType.Consumer, null, (context) => {
        let { dateEnv, options } = context;
        let { date } = props;
        let format = options.weekNumberFormat || props.defaultFormat;
        let num = dateEnv.computeWeekNumber(date); // TODO: somehow use for formatting as well?
        let text = dateEnv.format(date, format);
        let renderProps = { num, text, date };
        return (y(ContentContainer // why isn't WeekNumberContentArg being auto-detected?
        , { elRef: props.elRef, elTag: props.elTag, elAttrs: props.elAttrs, elClasses: props.elClasses, elStyle: props.elStyle, renderProps: renderProps, generatorName: "weekNumberContent", customGenerator: options.weekNumberContent, defaultGenerator: renderInner, classNameGenerator: options.weekNumberClassNames, didMount: options.weekNumberDidMount, willUnmount: options.weekNumberWillUnmount }, props.children));
    }));
    function renderInner(innerProps) {
        return innerProps.text;
    }

    const PADDING_FROM_VIEWPORT = 10;
    class Popover extends BaseComponent {
        constructor() {
            super(...arguments);
            this.state = {
                titleId: getUniqueDomId(),
            };
            this.handleRootEl = (el) => {
                this.rootEl = el;
                if (this.props.elRef) {
                    setRef(this.props.elRef, el);
                }
            };
            // Triggered when the user clicks *anywhere* in the document, for the autoHide feature
            this.handleDocumentMouseDown = (ev) => {
                // only hide the popover if the click happened outside the popover
                const target = getEventTargetViaRoot(ev);
                if (!this.rootEl.contains(target)) {
                    this.handleCloseClick();
                }
            };
            this.handleDocumentKeyDown = (ev) => {
                if (ev.key === 'Escape') {
                    this.handleCloseClick();
                }
            };
            this.handleCloseClick = () => {
                let { onClose } = this.props;
                if (onClose) {
                    onClose();
                }
            };
        }
        render() {
            let { theme, options } = this.context;
            let { props, state } = this;
            let classNames = [
                'fc-popover',
                theme.getClass('popover'),
            ].concat(props.extraClassNames || []);
            return j(y("div", Object.assign({}, props.extraAttrs, { id: props.id, className: classNames.join(' '), "aria-labelledby": state.titleId, ref: this.handleRootEl }),
                y("div", { className: 'fc-popover-header ' + theme.getClass('popoverHeader') },
                    y("span", { className: "fc-popover-title", id: state.titleId }, props.title),
                    y("span", { className: 'fc-popover-close ' + theme.getIconClass('close'), title: options.closeHint, onClick: this.handleCloseClick })),
                y("div", { className: 'fc-popover-body ' + theme.getClass('popoverContent') }, props.children)), props.parentEl);
        }
        componentDidMount() {
            document.addEventListener('mousedown', this.handleDocumentMouseDown);
            document.addEventListener('keydown', this.handleDocumentKeyDown);
            this.updateSize();
        }
        componentWillUnmount() {
            document.removeEventListener('mousedown', this.handleDocumentMouseDown);
            document.removeEventListener('keydown', this.handleDocumentKeyDown);
        }
        updateSize() {
            let { isRtl } = this.context;
            let { alignmentEl, alignGridTop } = this.props;
            let { rootEl } = this;
            let alignmentRect = computeClippedClientRect(alignmentEl);
            if (alignmentRect) {
                let popoverDims = rootEl.getBoundingClientRect();
                // position relative to viewport
                let popoverTop = alignGridTop
                    ? elementClosest(alignmentEl, '.fc-scrollgrid').getBoundingClientRect().top
                    : alignmentRect.top;
                let popoverLeft = isRtl ? alignmentRect.right - popoverDims.width : alignmentRect.left;
                // constrain
                popoverTop = Math.max(popoverTop, PADDING_FROM_VIEWPORT);
                popoverLeft = Math.min(popoverLeft, document.documentElement.clientWidth - PADDING_FROM_VIEWPORT - popoverDims.width);
                popoverLeft = Math.max(popoverLeft, PADDING_FROM_VIEWPORT);
                let origin = rootEl.offsetParent.getBoundingClientRect();
                applyStyle(rootEl, {
                    top: popoverTop - origin.top,
                    left: popoverLeft - origin.left,
                });
            }
        }
    }

    class MorePopover extends DateComponent {
        constructor() {
            super(...arguments);
            this.handleRootEl = (rootEl) => {
                this.rootEl = rootEl;
                if (rootEl) {
                    this.context.registerInteractiveComponent(this, {
                        el: rootEl,
                        useEventCenter: false,
                    });
                }
                else {
                    this.context.unregisterInteractiveComponent(this);
                }
            };
        }
        render() {
            let { options, dateEnv } = this.context;
            let { props } = this;
            let { startDate, todayRange, dateProfile } = props;
            let title = dateEnv.format(startDate, options.dayPopoverFormat);
            return (y(DayCellContainer, { elRef: this.handleRootEl, date: startDate, dateProfile: dateProfile, todayRange: todayRange }, (InnerContent, renderProps, elAttrs) => (y(Popover, { elRef: elAttrs.ref, id: props.id, title: title, extraClassNames: ['fc-more-popover'].concat(elAttrs.className || []), extraAttrs: elAttrs /* TODO: make these time-based when not whole-day? */, parentEl: props.parentEl, alignmentEl: props.alignmentEl, alignGridTop: props.alignGridTop, onClose: props.onClose },
                hasCustomDayCellContent(options) && (y(InnerContent, { elTag: "div", elClasses: ['fc-more-popover-misc'] })),
                props.children))));
        }
        queryHit(positionLeft, positionTop, elWidth, elHeight) {
            let { rootEl, props } = this;
            if (positionLeft >= 0 && positionLeft < elWidth &&
                positionTop >= 0 && positionTop < elHeight) {
                return {
                    dateProfile: props.dateProfile,
                    dateSpan: Object.assign({ allDay: !props.forceTimed, range: {
                            start: props.startDate,
                            end: props.endDate,
                        } }, props.extraDateSpan),
                    dayEl: rootEl,
                    rect: {
                        left: 0,
                        top: 0,
                        right: elWidth,
                        bottom: elHeight,
                    },
                    layer: 1, // important when comparing with hits from other components
                };
            }
            return null;
        }
    }

    class MoreLinkContainer extends BaseComponent {
        constructor() {
            super(...arguments);
            this.state = {
                isPopoverOpen: false,
                popoverId: getUniqueDomId(),
            };
            this.handleLinkEl = (linkEl) => {
                this.linkEl = linkEl;
                if (this.props.elRef) {
                    setRef(this.props.elRef, linkEl);
                }
            };
            this.handleClick = (ev) => {
                let { props, context } = this;
                let { moreLinkClick } = context.options;
                let date = computeRange(props).start;
                function buildPublicSeg(seg) {
                    let { def, instance, range } = seg.eventRange;
                    return {
                        event: new EventImpl(context, def, instance),
                        start: context.dateEnv.toDate(range.start),
                        end: context.dateEnv.toDate(range.end),
                        isStart: seg.isStart,
                        isEnd: seg.isEnd,
                    };
                }
                if (typeof moreLinkClick === 'function') {
                    moreLinkClick = moreLinkClick({
                        date,
                        allDay: Boolean(props.allDayDate),
                        allSegs: props.allSegs.map(buildPublicSeg),
                        hiddenSegs: props.hiddenSegs.map(buildPublicSeg),
                        jsEvent: ev,
                        view: context.viewApi,
                    });
                }
                if (!moreLinkClick || moreLinkClick === 'popover') {
                    this.setState({ isPopoverOpen: true });
                }
                else if (typeof moreLinkClick === 'string') { // a view name
                    context.calendarApi.zoomTo(date, moreLinkClick);
                }
            };
            this.handlePopoverClose = () => {
                this.setState({ isPopoverOpen: false });
            };
        }
        render() {
            let { props, state } = this;
            return (y(ViewContextType.Consumer, null, (context) => {
                let { viewApi, options, calendarApi } = context;
                let { moreLinkText } = options;
                let { moreCnt } = props;
                let range = computeRange(props);
                let text = typeof moreLinkText === 'function' // TODO: eventually use formatWithOrdinals
                    ? moreLinkText.call(calendarApi, moreCnt)
                    : `+${moreCnt} ${moreLinkText}`;
                let hint = formatWithOrdinals(options.moreLinkHint, [moreCnt], text);
                let renderProps = {
                    num: moreCnt,
                    shortText: `+${moreCnt}`,
                    text,
                    view: viewApi,
                };
                return (y(_, null,
                    Boolean(props.moreCnt) && (y(ContentContainer, { elTag: props.elTag || 'a', elRef: this.handleLinkEl, elClasses: [
                            ...(props.elClasses || []),
                            'fc-more-link',
                        ], elStyle: props.elStyle, elAttrs: Object.assign(Object.assign(Object.assign({}, props.elAttrs), createAriaClickAttrs(this.handleClick)), { title: hint, 'aria-expanded': state.isPopoverOpen, 'aria-controls': state.isPopoverOpen ? state.popoverId : '' }), renderProps: renderProps, generatorName: "moreLinkContent", customGenerator: options.moreLinkContent, defaultGenerator: props.defaultGenerator || renderMoreLinkInner, classNameGenerator: options.moreLinkClassNames, didMount: options.moreLinkDidMount, willUnmount: options.moreLinkWillUnmount }, props.children)),
                    state.isPopoverOpen && (y(MorePopover, { id: state.popoverId, startDate: range.start, endDate: range.end, dateProfile: props.dateProfile, todayRange: props.todayRange, extraDateSpan: props.extraDateSpan, parentEl: this.parentEl, alignmentEl: props.alignmentElRef ?
                            props.alignmentElRef.current :
                            this.linkEl, alignGridTop: props.alignGridTop, forceTimed: props.forceTimed, onClose: this.handlePopoverClose }, props.popoverContent()))));
            }));
        }
        componentDidMount() {
            this.updateParentEl();
        }
        componentDidUpdate() {
            this.updateParentEl();
        }
        updateParentEl() {
            if (this.linkEl) {
                this.parentEl = elementClosest(this.linkEl, '.fc-view-harness');
            }
        }
    }
    function renderMoreLinkInner(props) {
        return props.text;
    }
    function computeRange(props) {
        if (props.allDayDate) {
            return {
                start: props.allDayDate,
                end: addDays(props.allDayDate, 1),
            };
        }
        let { hiddenSegs } = props;
        return {
            start: computeEarliestSegStart(hiddenSegs),
            end: computeLatestSegEnd(hiddenSegs),
        };
    }
    function computeEarliestSegStart(segs) {
        return segs.reduce(pickEarliestStart).eventRange.range.start;
    }
    function pickEarliestStart(seg0, seg1) {
        return seg0.eventRange.range.start < seg1.eventRange.range.start ? seg0 : seg1;
    }
    function computeLatestSegEnd(segs) {
        return segs.reduce(pickLatestEnd).eventRange.range.end;
    }
    function pickLatestEnd(seg0, seg1) {
        return seg0.eventRange.range.end > seg1.eventRange.range.end ? seg0 : seg1;
    }

    class ViewContainer extends BaseComponent {
        render() {
            let { props, context } = this;
            let { options } = context;
            let renderProps = { view: context.viewApi };
            return (y(ContentContainer, { elRef: props.elRef, elTag: props.elTag || 'div', elAttrs: props.elAttrs, elClasses: [
                    ...buildViewClassNames(props.viewSpec),
                    ...(props.elClasses || []),
                ], elStyle: props.elStyle, renderProps: renderProps, classNameGenerator: options.viewClassNames, generatorName: undefined, didMount: options.viewDidMount, willUnmount: options.viewWillUnmount }, () => props.children));
        }
    }
    function buildViewClassNames(viewSpec) {
        return [
            `fc-${viewSpec.type}-view`,
            'fc-view',
        ];
    }

    const EVENT_SOURCE_REFINERS = {
        id: String,
        defaultAllDay: Boolean,
        url: String,
        format: String,
        events: identity,
        eventDataTransform: identity,
        // for any network-related sources
        success: identity,
        failure: identity,
    };
    function parseEventSource(raw, context, refiners = buildEventSourceRefiners(context)) {
        let rawObj;
        if (typeof raw === 'string') {
            rawObj = { url: raw };
        }
        else if (typeof raw === 'function' || Array.isArray(raw)) {
            rawObj = { events: raw };
        }
        else if (typeof raw === 'object' && raw) { // not null
            rawObj = raw;
        }
        if (rawObj) {
            let { refined, extra } = refineProps(rawObj, refiners);
            let metaRes = buildEventSourceMeta(refined, context);
            if (metaRes) {
                return {
                    _raw: raw,
                    isFetching: false,
                    latestFetchId: '',
                    fetchRange: null,
                    defaultAllDay: refined.defaultAllDay,
                    eventDataTransform: refined.eventDataTransform,
                    success: refined.success,
                    failure: refined.failure,
                    publicId: refined.id || '',
                    sourceId: guid(),
                    sourceDefId: metaRes.sourceDefId,
                    meta: metaRes.meta,
                    ui: createEventUi(refined, context),
                    extendedProps: extra,
                };
            }
        }
        return null;
    }
    function buildEventSourceRefiners(context) {
        return Object.assign(Object.assign(Object.assign({}, EVENT_UI_REFINERS), EVENT_SOURCE_REFINERS), context.pluginHooks.eventSourceRefiners);
    }
    function buildEventSourceMeta(raw, context) {
        let defs = context.pluginHooks.eventSourceDefs;
        for (let i = defs.length - 1; i >= 0; i -= 1) { // later-added plugins take precedence
            let def = defs[i];
            let meta = def.parseMeta(raw);
            if (meta) {
                return { sourceDefId: i, meta };
            }
        }
        return null;
    }

    class CalendarImpl {
        getCurrentData() {
            return this.currentDataManager.getCurrentData();
        }
        dispatch(action) {
            this.currentDataManager.dispatch(action);
        }
        get view() { return this.getCurrentData().viewApi; }
        batchRendering(callback) {
            callback();
        }
        updateSize() {
            this.trigger('_resize', true);
        }
        // Options
        // -----------------------------------------------------------------------------------------------------------------
        setOption(name, val) {
            this.dispatch({
                type: 'SET_OPTION',
                optionName: name,
                rawOptionValue: val,
            });
        }
        getOption(name) {
            return this.currentDataManager.currentCalendarOptionsInput[name];
        }
        getAvailableLocaleCodes() {
            return Object.keys(this.getCurrentData().availableRawLocales);
        }
        // Trigger
        // -----------------------------------------------------------------------------------------------------------------
        on(handlerName, handler) {
            let { currentDataManager } = this;
            if (currentDataManager.currentCalendarOptionsRefiners[handlerName]) {
                currentDataManager.emitter.on(handlerName, handler);
            }
            else {
                console.warn(`Unknown listener name '${handlerName}'`);
            }
        }
        off(handlerName, handler) {
            this.currentDataManager.emitter.off(handlerName, handler);
        }
        // not meant for public use
        trigger(handlerName, ...args) {
            this.currentDataManager.emitter.trigger(handlerName, ...args);
        }
        // View
        // -----------------------------------------------------------------------------------------------------------------
        changeView(viewType, dateOrRange) {
            this.batchRendering(() => {
                this.unselect();
                if (dateOrRange) {
                    if (dateOrRange.start && dateOrRange.end) { // a range
                        this.dispatch({
                            type: 'CHANGE_VIEW_TYPE',
                            viewType,
                        });
                        this.dispatch({
                            type: 'SET_OPTION',
                            optionName: 'visibleRange',
                            rawOptionValue: dateOrRange,
                        });
                    }
                    else {
                        let { dateEnv } = this.getCurrentData();
                        this.dispatch({
                            type: 'CHANGE_VIEW_TYPE',
                            viewType,
                            dateMarker: dateEnv.createMarker(dateOrRange),
                        });
                    }
                }
                else {
                    this.dispatch({
                        type: 'CHANGE_VIEW_TYPE',
                        viewType,
                    });
                }
            });
        }
        // Forces navigation to a view for the given date.
        // `viewType` can be a specific view name or a generic one like "week" or "day".
        // needs to change
        zoomTo(dateMarker, viewType) {
            let state = this.getCurrentData();
            let spec;
            viewType = viewType || 'day'; // day is default zoom
            spec = state.viewSpecs[viewType] || this.getUnitViewSpec(viewType);
            this.unselect();
            if (spec) {
                this.dispatch({
                    type: 'CHANGE_VIEW_TYPE',
                    viewType: spec.type,
                    dateMarker,
                });
            }
            else {
                this.dispatch({
                    type: 'CHANGE_DATE',
                    dateMarker,
                });
            }
        }
        // Given a duration singular unit, like "week" or "day", finds a matching view spec.
        // Preference is given to views that have corresponding buttons.
        getUnitViewSpec(unit) {
            let { viewSpecs, toolbarConfig } = this.getCurrentData();
            let viewTypes = [].concat(toolbarConfig.header ? toolbarConfig.header.viewsWithButtons : [], toolbarConfig.footer ? toolbarConfig.footer.viewsWithButtons : []);
            let i;
            let spec;
            for (let viewType in viewSpecs) {
                viewTypes.push(viewType);
            }
            for (i = 0; i < viewTypes.length; i += 1) {
                spec = viewSpecs[viewTypes[i]];
                if (spec) {
                    if (spec.singleUnit === unit) {
                        return spec;
                    }
                }
            }
            return null;
        }
        // Current Date
        // -----------------------------------------------------------------------------------------------------------------
        prev() {
            this.unselect();
            this.dispatch({ type: 'PREV' });
        }
        next() {
            this.unselect();
            this.dispatch({ type: 'NEXT' });
        }
        prevYear() {
            let state = this.getCurrentData();
            this.unselect();
            this.dispatch({
                type: 'CHANGE_DATE',
                dateMarker: state.dateEnv.addYears(state.currentDate, -1),
            });
        }
        nextYear() {
            let state = this.getCurrentData();
            this.unselect();
            this.dispatch({
                type: 'CHANGE_DATE',
                dateMarker: state.dateEnv.addYears(state.currentDate, 1),
            });
        }
        today() {
            let state = this.getCurrentData();
            this.unselect();
            this.dispatch({
                type: 'CHANGE_DATE',
                dateMarker: state.nowManager.getDateMarker(),
            });
        }
        gotoDate(zonedDateInput) {
            let state = this.getCurrentData();
            this.unselect();
            this.dispatch({
                type: 'CHANGE_DATE',
                dateMarker: state.dateEnv.createMarker(zonedDateInput),
            });
        }
        incrementDate(deltaInput) {
            let state = this.getCurrentData();
            let delta = createDuration(deltaInput);
            if (delta) { // else, warn about invalid input?
                this.unselect();
                this.dispatch({
                    type: 'CHANGE_DATE',
                    dateMarker: state.dateEnv.add(state.currentDate, delta),
                });
            }
        }
        getDate() {
            let state = this.getCurrentData();
            return state.dateEnv.toDate(state.currentDate);
        }
        // Date Formatting Utils
        // -----------------------------------------------------------------------------------------------------------------
        formatDate(d, formatter) {
            let { dateEnv } = this.getCurrentData();
            return dateEnv.format(dateEnv.createMarker(d), createFormatter(formatter));
        }
        // `settings` is for formatter AND isEndExclusive
        formatRange(d0, d1, settings) {
            let { dateEnv } = this.getCurrentData();
            return dateEnv.formatRange(dateEnv.createMarker(d0), dateEnv.createMarker(d1), createFormatter(settings), settings);
        }
        formatIso(d, omitTime) {
            let { dateEnv } = this.getCurrentData();
            return dateEnv.formatIso(dateEnv.createMarker(d), { omitTime });
        }
        // Date Selection / Event Selection / DayClick
        // -----------------------------------------------------------------------------------------------------------------
        select(dateOrObj, endDate) {
            let selectionInput;
            if (endDate == null) {
                if (dateOrObj.start != null) {
                    selectionInput = dateOrObj;
                }
                else {
                    selectionInput = {
                        start: dateOrObj,
                        end: null,
                    };
                }
            }
            else {
                selectionInput = {
                    start: dateOrObj,
                    end: endDate,
                };
            }
            let state = this.getCurrentData();
            let selection = parseDateSpan(selectionInput, state.dateEnv, createDuration({ days: 1 }));
            if (selection) { // throw parse error otherwise?
                this.dispatch({ type: 'SELECT_DATES', selection });
                triggerDateSelect(selection, null, state);
            }
        }
        unselect(pev) {
            let state = this.getCurrentData();
            if (state.dateSelection) {
                this.dispatch({ type: 'UNSELECT_DATES' });
                triggerDateUnselect(pev, state);
            }
        }
        // Public Events API
        // -----------------------------------------------------------------------------------------------------------------
        addEvent(eventInput, sourceInput) {
            if (eventInput instanceof EventImpl) {
                let def = eventInput._def;
                let instance = eventInput._instance;
                let currentData = this.getCurrentData();
                // not already present? don't want to add an old snapshot
                if (!currentData.eventStore.defs[def.defId]) {
                    this.dispatch({
                        type: 'ADD_EVENTS',
                        eventStore: eventTupleToStore({ def, instance }), // TODO: better util for two args?
                    });
                    this.triggerEventAdd(eventInput);
                }
                return eventInput;
            }
            let state = this.getCurrentData();
            let eventSource;
            if (sourceInput instanceof EventSourceImpl) {
                eventSource = sourceInput.internalEventSource;
            }
            else if (typeof sourceInput === 'boolean') {
                if (sourceInput) { // true. part of the first event source
                    [eventSource] = hashValuesToArray(state.eventSources);
                }
            }
            else if (sourceInput != null) { // an ID. accepts a number too
                let sourceApi = this.getEventSourceById(sourceInput); // TODO: use an internal function
                if (!sourceApi) {
                    console.warn(`Could not find an event source with ID "${sourceInput}"`); // TODO: test
                    return null;
                }
                eventSource = sourceApi.internalEventSource;
            }
            let tuple = parseEvent(eventInput, eventSource, state, false);
            if (tuple) {
                let newEventApi = new EventImpl(state, tuple.def, tuple.def.recurringDef ? null : tuple.instance);
                this.dispatch({
                    type: 'ADD_EVENTS',
                    eventStore: eventTupleToStore(tuple),
                });
                this.triggerEventAdd(newEventApi);
                return newEventApi;
            }
            return null;
        }
        triggerEventAdd(eventApi) {
            let { emitter } = this.getCurrentData();
            emitter.trigger('eventAdd', {
                event: eventApi,
                relatedEvents: [],
                revert: () => {
                    this.dispatch({
                        type: 'REMOVE_EVENTS',
                        eventStore: eventApiToStore(eventApi),
                    });
                },
            });
        }
        // TODO: optimize
        getEventById(id) {
            let state = this.getCurrentData();
            let { defs, instances } = state.eventStore;
            id = String(id);
            for (let defId in defs) {
                let def = defs[defId];
                if (def.publicId === id) {
                    if (def.recurringDef) {
                        return new EventImpl(state, def, null);
                    }
                    for (let instanceId in instances) {
                        let instance = instances[instanceId];
                        if (instance.defId === def.defId) {
                            return new EventImpl(state, def, instance);
                        }
                    }
                }
            }
            return null;
        }
        getEvents() {
            let currentData = this.getCurrentData();
            return buildEventApis(currentData.eventStore, currentData);
        }
        removeAllEvents() {
            this.dispatch({ type: 'REMOVE_ALL_EVENTS' });
        }
        // Public Event Sources API
        // -----------------------------------------------------------------------------------------------------------------
        getEventSources() {
            let state = this.getCurrentData();
            let sourceHash = state.eventSources;
            let sourceApis = [];
            for (let internalId in sourceHash) {
                sourceApis.push(new EventSourceImpl(state, sourceHash[internalId]));
            }
            return sourceApis;
        }
        getEventSourceById(id) {
            let state = this.getCurrentData();
            let sourceHash = state.eventSources;
            id = String(id);
            for (let sourceId in sourceHash) {
                if (sourceHash[sourceId].publicId === id) {
                    return new EventSourceImpl(state, sourceHash[sourceId]);
                }
            }
            return null;
        }
        addEventSource(sourceInput) {
            let state = this.getCurrentData();
            if (sourceInput instanceof EventSourceImpl) {
                // not already present? don't want to add an old snapshot
                if (!state.eventSources[sourceInput.internalEventSource.sourceId]) {
                    this.dispatch({
                        type: 'ADD_EVENT_SOURCES',
                        sources: [sourceInput.internalEventSource],
                    });
                }
                return sourceInput;
            }
            let eventSource = parseEventSource(sourceInput, state);
            if (eventSource) { // TODO: error otherwise?
                this.dispatch({ type: 'ADD_EVENT_SOURCES', sources: [eventSource] });
                return new EventSourceImpl(state, eventSource);
            }
            return null;
        }
        removeAllEventSources() {
            this.dispatch({ type: 'REMOVE_ALL_EVENT_SOURCES' });
        }
        refetchEvents() {
            this.dispatch({ type: 'FETCH_EVENT_SOURCES', isRefetch: true });
        }
        // Scroll
        // -----------------------------------------------------------------------------------------------------------------
        scrollToTime(timeInput) {
            let time = createDuration(timeInput);
            if (time) {
                this.trigger('_scrollRequest', { time });
            }
        }
    }

    class Store {
        constructor() {
            this.handlers = [];
        }
        set(value) {
            this.currentValue = value;
            for (let handler of this.handlers) {
                handler(value);
            }
        }
        subscribe(handler) {
            this.handlers.push(handler);
            if (this.currentValue !== undefined) {
                handler(this.currentValue);
            }
        }
    }

    /*
    Subscribers will get a LIST of CustomRenderings
    */
    class CustomRenderingStore extends Store {
        constructor() {
            super(...arguments);
            this.map = new Map();
        }
        // for consistent order
        handle(customRendering) {
            const { map } = this;
            let updated = false;
            if (customRendering.isActive) {
                map.set(customRendering.id, customRendering);
                updated = true;
            }
            else if (map.has(customRendering.id)) {
                map.delete(customRendering.id);
                updated = true;
            }
            if (updated) {
                this.set(map);
            }
        }
    }

    var internal = {
        __proto__: null,
        BASE_OPTION_DEFAULTS: BASE_OPTION_DEFAULTS,
        identity: identity,
        refineProps: refineProps,
        createEventInstance: createEventInstance,
        parseEventDef: parseEventDef,
        refineEventDef: refineEventDef,
        parseBusinessHours: parseBusinessHours,
        padStart: padStart,
        isInt: isInt,
        parseFieldSpecs: parseFieldSpecs,
        compareByFieldSpecs: compareByFieldSpecs,
        flexibleCompare: flexibleCompare,
        preventSelection: preventSelection,
        allowSelection: allowSelection,
        preventContextMenu: preventContextMenu,
        allowContextMenu: allowContextMenu,
        compareNumbers: compareNumbers,
        enableCursor: enableCursor,
        disableCursor: disableCursor,
        guid: guid,
        computeVisibleDayRange: computeVisibleDayRange,
        isMultiDayRange: isMultiDayRange,
        diffDates: diffDates,
        removeExact: removeExact,
        isArraysEqual: isArraysEqual,
        memoize: memoize,
        memoizeObjArg: memoizeObjArg,
        memoizeArraylike: memoizeArraylike,
        memoizeHashlike: memoizeHashlike,
        intersectRects: intersectRects,
        pointInsideRect: pointInsideRect,
        constrainPoint: constrainPoint,
        getRectCenter: getRectCenter,
        diffPoints: diffPoints,
        translateRect: translateRect,
        mapHash: mapHash,
        filterHash: filterHash,
        isPropsEqual: isPropsEqual,
        compareObjs: compareObjs,
        collectFromHash: collectFromHash,
        findElements: findElements,
        findDirectChildren: findDirectChildren,
        removeElement: removeElement,
        applyStyle: applyStyle,
        elementMatches: elementMatches,
        elementClosest: elementClosest,
        getEventTargetViaRoot: getEventTargetViaRoot,
        getUniqueDomId: getUniqueDomId,
        parseClassNames: parseClassNames,
        getCanVGrowWithinCell: getCanVGrowWithinCell,
        createEmptyEventStore: createEmptyEventStore,
        mergeEventStores: mergeEventStores,
        getRelevantEvents: getRelevantEvents,
        eventTupleToStore: eventTupleToStore,
        combineEventUis: combineEventUis,
        createEventUi: createEventUi,
        Splitter: Splitter,
        getDayClassNames: getDayClassNames,
        getDateMeta: getDateMeta,
        getSlotClassNames: getSlotClassNames,
        buildNavLinkAttrs: buildNavLinkAttrs,
        preventDefault: preventDefault,
        whenTransitionDone: whenTransitionDone,
        computeInnerRect: computeInnerRect,
        computeEdges: computeEdges,
        getClippingParents: getClippingParents,
        computeRect: computeRect,
        unpromisify: unpromisify,
        Emitter: Emitter,
        rangeContainsMarker: rangeContainsMarker,
        intersectRanges: intersectRanges,
        rangesEqual: rangesEqual,
        rangesIntersect: rangesIntersect,
        rangeContainsRange: rangeContainsRange,
        PositionCache: PositionCache,
        ScrollController: ScrollController,
        ElementScrollController: ElementScrollController,
        WindowScrollController: WindowScrollController,
        Theme: Theme,
        ViewContextType: ViewContextType,
        DateComponent: DateComponent,
        DateProfileGenerator: DateProfileGenerator,
        isDateSpansEqual: isDateSpansEqual,
        addDays: addDays,
        startOfDay: startOfDay,
        addMs: addMs,
        addWeeks: addWeeks,
        diffWeeks: diffWeeks,
        diffWholeWeeks: diffWholeWeeks,
        diffWholeDays: diffWholeDays,
        diffDayAndTime: diffDayAndTime,
        diffDays: diffDays,
        isValidDate: isValidDate,
        createDuration: createDuration,
        asCleanDays: asCleanDays,
        multiplyDuration: multiplyDuration,
        addDurations: addDurations,
        asRoughMinutes: asRoughMinutes,
        asRoughSeconds: asRoughSeconds,
        asRoughMs: asRoughMs,
        wholeDivideDurations: wholeDivideDurations,
        greatestDurationDenominator: greatestDurationDenominator,
        DateEnv: DateEnv,
        createFormatter: createFormatter,
        formatIsoTimeString: formatIsoTimeString,
        formatDayString: formatDayString,
        buildIsoString: buildIsoString,
        formatIsoMonthStr: formatIsoMonthStr,
        NamedTimeZoneImpl: NamedTimeZoneImpl,
        parseMarker: parse,
        SegHierarchy: SegHierarchy,
        buildEntryKey: buildEntryKey,
        getEntrySpanEnd: getEntrySpanEnd,
        binarySearch: binarySearch,
        groupIntersectingEntries: groupIntersectingEntries,
        intersectSpans: intersectSpans,
        Interaction: Interaction,
        interactionSettingsToStore: interactionSettingsToStore,
        interactionSettingsStore: interactionSettingsStore,
        ElementDragging: ElementDragging,
        config: config,
        parseDragMeta: parseDragMeta,
        CalendarRoot: CalendarRoot,
        DayHeader: DayHeader,
        computeFallbackHeaderFormat: computeFallbackHeaderFormat,
        TableDateCell: TableDateCell,
        TableDowCell: TableDowCell,
        DaySeriesModel: DaySeriesModel,
        sliceEventStore: sliceEventStore,
        hasBgRendering: hasBgRendering,
        getElSeg: getElSeg,
        buildSegTimeText: buildSegTimeText,
        sortEventSegs: sortEventSegs,
        getSegMeta: getSegMeta,
        buildEventRangeKey: buildEventRangeKey,
        getSegAnchorAttrs: getSegAnchorAttrs,
        DayTableModel: DayTableModel,
        Slicer: Slicer,
        applyMutationToEventStore: applyMutationToEventStore,
        isPropsValid: isPropsValid,
        isInteractionValid: isInteractionValid,
        isDateSelectionValid: isDateSelectionValid,
        requestJson: requestJson,
        BaseComponent: BaseComponent,
        setRef: setRef,
        DelayedRunner: DelayedRunner,
        SimpleScrollGrid: SimpleScrollGrid,
        hasShrinkWidth: hasShrinkWidth,
        renderMicroColGroup: renderMicroColGroup,
        getScrollGridClassNames: getScrollGridClassNames,
        getSectionClassNames: getSectionClassNames,
        getSectionHasLiquidHeight: getSectionHasLiquidHeight,
        getAllowYScrolling: getAllowYScrolling,
        renderChunkContent: renderChunkContent,
        computeShrinkWidth: computeShrinkWidth,
        sanitizeShrinkWidth: sanitizeShrinkWidth,
        isColPropsEqual: isColPropsEqual,
        renderScrollShim: renderScrollShim,
        getStickyFooterScrollbar: getStickyFooterScrollbar,
        getStickyHeaderDates: getStickyHeaderDates,
        Scroller: Scroller,
        getScrollbarWidths: getScrollbarWidths,
        RefMap: RefMap,
        getIsRtlScrollbarOnLeft: getIsRtlScrollbarOnLeft,
        NowTimer: NowTimer,
        ScrollResponder: ScrollResponder,
        StandardEvent: StandardEvent,
        NowIndicatorContainer: NowIndicatorContainer,
        DayCellContainer: DayCellContainer,
        hasCustomDayCellContent: hasCustomDayCellContent,
        EventContainer: EventContainer,
        renderFill: renderFill,
        BgEvent: BgEvent,
        WeekNumberContainer: WeekNumberContainer,
        MoreLinkContainer: MoreLinkContainer,
        computeEarliestSegStart: computeEarliestSegStart,
        ViewContainer: ViewContainer,
        triggerDateSelect: triggerDateSelect,
        getDefaultEventEnd: getDefaultEventEnd,
        injectStyles: injectStyles,
        CalendarImpl: CalendarImpl,
        EventImpl: EventImpl,
        buildEventApis: buildEventApis,
        buildElAttrs: buildElAttrs,
        ContentContainer: ContentContainer,
        CustomRenderingStore: CustomRenderingStore
    };

    const globalLocales = [];

    const MINIMAL_RAW_EN_LOCALE = {
        code: 'en',
        week: {
            dow: 0,
            doy: 4, // 4 days need to be within the year to be considered the first week
        },
        direction: 'ltr',
        buttonText: {
            prev: 'prev',
            next: 'next',
            prevYear: 'prev year',
            nextYear: 'next year',
            year: 'year',
            today: 'today',
            month: 'month',
            week: 'week',
            day: 'day',
            list: 'list',
        },
        weekText: 'W',
        weekTextLong: 'Week',
        closeHint: 'Close',
        timeHint: 'Time',
        eventHint: 'Event',
        allDayText: 'all-day',
        moreLinkText: 'more',
        noEventsText: 'No events to display',
    };
    const RAW_EN_LOCALE = Object.assign(Object.assign({}, MINIMAL_RAW_EN_LOCALE), { 
        // Includes things we don't want other locales to inherit,
        // things that derive from other translatable strings.
        buttonHints: {
            prev: 'Previous $0',
            next: 'Next $0',
            today(buttonText, unit) {
                return (unit === 'day')
                    ? 'Today'
                    : `This ${buttonText}`;
            },
        }, viewHint: '$0 view', navLinkHint: 'Go to $0', moreLinkHint(eventCnt) {
            return `Show ${eventCnt} more event${eventCnt === 1 ? '' : 's'}`;
        } });
    function organizeRawLocales(explicitRawLocales) {
        let defaultCode = explicitRawLocales.length > 0 ? explicitRawLocales[0].code : 'en';
        let allRawLocales = globalLocales.concat(explicitRawLocales);
        let rawLocaleMap = {
            en: RAW_EN_LOCALE,
        };
        for (let rawLocale of allRawLocales) {
            rawLocaleMap[rawLocale.code] = rawLocale;
        }
        return {
            map: rawLocaleMap,
            defaultCode,
        };
    }
    function buildLocale(inputSingular, available) {
        if (typeof inputSingular === 'object' && !Array.isArray(inputSingular)) {
            return parseLocale(inputSingular.code, [inputSingular.code], inputSingular);
        }
        return queryLocale(inputSingular, available);
    }
    function queryLocale(codeArg, available) {
        let codes = [].concat(codeArg || []); // will convert to array
        let raw = queryRawLocale(codes, available) || RAW_EN_LOCALE;
        return parseLocale(codeArg, codes, raw);
    }
    function queryRawLocale(codes, available) {
        for (let i = 0; i < codes.length; i += 1) {
            let parts = codes[i].toLocaleLowerCase().split('-');
            for (let j = parts.length; j > 0; j -= 1) {
                let simpleId = parts.slice(0, j).join('-');
                if (available[simpleId]) {
                    return available[simpleId];
                }
            }
        }
        return null;
    }
    function parseLocale(codeArg, codes, raw) {
        let merged = mergeProps([MINIMAL_RAW_EN_LOCALE, raw], ['buttonText']);
        delete merged.code; // don't want this part of the options
        let { week } = merged;
        delete merged.week;
        return {
            codeArg,
            codes,
            week,
            simpleNumberFormat: new Intl.NumberFormat(codeArg),
            options: merged,
        };
    }

    // TODO: easier way to add new hooks? need to update a million things
    function createPlugin(input) {
        return {
            id: guid(),
            name: input.name,
            premiumReleaseDate: input.premiumReleaseDate ? new Date(input.premiumReleaseDate) : undefined,
            deps: input.deps || [],
            reducers: input.reducers || [],
            isLoadingFuncs: input.isLoadingFuncs || [],
            contextInit: [].concat(input.contextInit || []),
            eventRefiners: input.eventRefiners || {},
            eventDefMemberAdders: input.eventDefMemberAdders || [],
            eventSourceRefiners: input.eventSourceRefiners || {},
            isDraggableTransformers: input.isDraggableTransformers || [],
            eventDragMutationMassagers: input.eventDragMutationMassagers || [],
            eventDefMutationAppliers: input.eventDefMutationAppliers || [],
            dateSelectionTransformers: input.dateSelectionTransformers || [],
            datePointTransforms: input.datePointTransforms || [],
            dateSpanTransforms: input.dateSpanTransforms || [],
            views: input.views || {},
            viewPropsTransformers: input.viewPropsTransformers || [],
            isPropsValid: input.isPropsValid || null,
            externalDefTransforms: input.externalDefTransforms || [],
            viewContainerAppends: input.viewContainerAppends || [],
            eventDropTransformers: input.eventDropTransformers || [],
            componentInteractions: input.componentInteractions || [],
            calendarInteractions: input.calendarInteractions || [],
            themeClasses: input.themeClasses || {},
            eventSourceDefs: input.eventSourceDefs || [],
            cmdFormatter: input.cmdFormatter,
            recurringTypes: input.recurringTypes || [],
            namedTimeZonedImpl: input.namedTimeZonedImpl,
            initialView: input.initialView || '',
            elementDraggingImpl: input.elementDraggingImpl,
            optionChangeHandlers: input.optionChangeHandlers || {},
            scrollGridImpl: input.scrollGridImpl || null,
            listenerRefiners: input.listenerRefiners || {},
            optionRefiners: input.optionRefiners || {},
            propSetHandlers: input.propSetHandlers || {},
        };
    }
    function buildPluginHooks(pluginDefs, globalDefs) {
        let currentPluginIds = {};
        let hooks = {
            premiumReleaseDate: undefined,
            reducers: [],
            isLoadingFuncs: [],
            contextInit: [],
            eventRefiners: {},
            eventDefMemberAdders: [],
            eventSourceRefiners: {},
            isDraggableTransformers: [],
            eventDragMutationMassagers: [],
            eventDefMutationAppliers: [],
            dateSelectionTransformers: [],
            datePointTransforms: [],
            dateSpanTransforms: [],
            views: {},
            viewPropsTransformers: [],
            isPropsValid: null,
            externalDefTransforms: [],
            viewContainerAppends: [],
            eventDropTransformers: [],
            componentInteractions: [],
            calendarInteractions: [],
            themeClasses: {},
            eventSourceDefs: [],
            cmdFormatter: null,
            recurringTypes: [],
            namedTimeZonedImpl: null,
            initialView: '',
            elementDraggingImpl: null,
            optionChangeHandlers: {},
            scrollGridImpl: null,
            listenerRefiners: {},
            optionRefiners: {},
            propSetHandlers: {},
        };
        function addDefs(defs) {
            for (let def of defs) {
                const pluginName = def.name;
                const currentId = currentPluginIds[pluginName];
                if (currentId === undefined) {
                    currentPluginIds[pluginName] = def.id;
                    addDefs(def.deps);
                    hooks = combineHooks(hooks, def);
                }
                else if (currentId !== def.id) {
                    // different ID than the one already added
                    console.warn(`Duplicate plugin '${pluginName}'`);
                }
            }
        }
        if (pluginDefs) {
            addDefs(pluginDefs);
        }
        addDefs(globalDefs);
        return hooks;
    }
    function buildBuildPluginHooks() {
        let currentOverrideDefs = [];
        let currentGlobalDefs = [];
        let currentHooks;
        return (overrideDefs, globalDefs) => {
            if (!currentHooks || !isArraysEqual(overrideDefs, currentOverrideDefs) || !isArraysEqual(globalDefs, currentGlobalDefs)) {
                currentHooks = buildPluginHooks(overrideDefs, globalDefs);
            }
            currentOverrideDefs = overrideDefs;
            currentGlobalDefs = globalDefs;
            return currentHooks;
        };
    }
    function combineHooks(hooks0, hooks1) {
        return {
            premiumReleaseDate: compareOptionalDates(hooks0.premiumReleaseDate, hooks1.premiumReleaseDate),
            reducers: hooks0.reducers.concat(hooks1.reducers),
            isLoadingFuncs: hooks0.isLoadingFuncs.concat(hooks1.isLoadingFuncs),
            contextInit: hooks0.contextInit.concat(hooks1.contextInit),
            eventRefiners: Object.assign(Object.assign({}, hooks0.eventRefiners), hooks1.eventRefiners),
            eventDefMemberAdders: hooks0.eventDefMemberAdders.concat(hooks1.eventDefMemberAdders),
            eventSourceRefiners: Object.assign(Object.assign({}, hooks0.eventSourceRefiners), hooks1.eventSourceRefiners),
            isDraggableTransformers: hooks0.isDraggableTransformers.concat(hooks1.isDraggableTransformers),
            eventDragMutationMassagers: hooks0.eventDragMutationMassagers.concat(hooks1.eventDragMutationMassagers),
            eventDefMutationAppliers: hooks0.eventDefMutationAppliers.concat(hooks1.eventDefMutationAppliers),
            dateSelectionTransformers: hooks0.dateSelectionTransformers.concat(hooks1.dateSelectionTransformers),
            datePointTransforms: hooks0.datePointTransforms.concat(hooks1.datePointTransforms),
            dateSpanTransforms: hooks0.dateSpanTransforms.concat(hooks1.dateSpanTransforms),
            views: Object.assign(Object.assign({}, hooks0.views), hooks1.views),
            viewPropsTransformers: hooks0.viewPropsTransformers.concat(hooks1.viewPropsTransformers),
            isPropsValid: hooks1.isPropsValid || hooks0.isPropsValid,
            externalDefTransforms: hooks0.externalDefTransforms.concat(hooks1.externalDefTransforms),
            viewContainerAppends: hooks0.viewContainerAppends.concat(hooks1.viewContainerAppends),
            eventDropTransformers: hooks0.eventDropTransformers.concat(hooks1.eventDropTransformers),
            calendarInteractions: hooks0.calendarInteractions.concat(hooks1.calendarInteractions),
            componentInteractions: hooks0.componentInteractions.concat(hooks1.componentInteractions),
            themeClasses: Object.assign(Object.assign({}, hooks0.themeClasses), hooks1.themeClasses),
            eventSourceDefs: hooks0.eventSourceDefs.concat(hooks1.eventSourceDefs),
            cmdFormatter: hooks1.cmdFormatter || hooks0.cmdFormatter,
            recurringTypes: hooks0.recurringTypes.concat(hooks1.recurringTypes),
            namedTimeZonedImpl: hooks1.namedTimeZonedImpl || hooks0.namedTimeZonedImpl,
            initialView: hooks0.initialView || hooks1.initialView,
            elementDraggingImpl: hooks0.elementDraggingImpl || hooks1.elementDraggingImpl,
            optionChangeHandlers: Object.assign(Object.assign({}, hooks0.optionChangeHandlers), hooks1.optionChangeHandlers),
            scrollGridImpl: hooks1.scrollGridImpl || hooks0.scrollGridImpl,
            listenerRefiners: Object.assign(Object.assign({}, hooks0.listenerRefiners), hooks1.listenerRefiners),
            optionRefiners: Object.assign(Object.assign({}, hooks0.optionRefiners), hooks1.optionRefiners),
            propSetHandlers: Object.assign(Object.assign({}, hooks0.propSetHandlers), hooks1.propSetHandlers),
        };
    }
    function compareOptionalDates(date0, date1) {
        if (date0 === undefined) {
            return date1;
        }
        if (date1 === undefined) {
            return date0;
        }
        return new Date(Math.max(date0.valueOf(), date1.valueOf()));
    }

    class StandardTheme extends Theme {
    }
    StandardTheme.prototype.classes = {
        root: 'fc-theme-standard',
        tableCellShaded: 'fc-cell-shaded',
        buttonGroup: 'fc-button-group',
        button: 'fc-button fc-button-primary',
        buttonActive: 'fc-button-active',
    };
    StandardTheme.prototype.baseIconClass = 'fc-icon';
    StandardTheme.prototype.iconClasses = {
        close: 'fc-icon-x',
        prev: 'fc-icon-chevron-left',
        next: 'fc-icon-chevron-right',
        prevYear: 'fc-icon-chevrons-left',
        nextYear: 'fc-icon-chevrons-right',
    };
    StandardTheme.prototype.rtlIconClasses = {
        prev: 'fc-icon-chevron-right',
        next: 'fc-icon-chevron-left',
        prevYear: 'fc-icon-chevrons-right',
        nextYear: 'fc-icon-chevrons-left',
    };
    StandardTheme.prototype.iconOverrideOption = 'buttonIcons'; // TODO: make TS-friendly
    StandardTheme.prototype.iconOverrideCustomButtonOption = 'icon';
    StandardTheme.prototype.iconOverridePrefix = 'fc-icon-';

    function compileViewDefs(defaultConfigs, overrideConfigs) {
        let hash = {};
        let viewType;
        for (viewType in defaultConfigs) {
            ensureViewDef(viewType, hash, defaultConfigs, overrideConfigs);
        }
        for (viewType in overrideConfigs) {
            ensureViewDef(viewType, hash, defaultConfigs, overrideConfigs);
        }
        return hash;
    }
    function ensureViewDef(viewType, hash, defaultConfigs, overrideConfigs) {
        if (hash[viewType]) {
            return hash[viewType];
        }
        let viewDef = buildViewDef(viewType, hash, defaultConfigs, overrideConfigs);
        if (viewDef) {
            hash[viewType] = viewDef;
        }
        return viewDef;
    }
    function buildViewDef(viewType, hash, defaultConfigs, overrideConfigs) {
        let defaultConfig = defaultConfigs[viewType];
        let overrideConfig = overrideConfigs[viewType];
        let queryProp = (name) => ((defaultConfig && defaultConfig[name] !== null) ? defaultConfig[name] :
            ((overrideConfig && overrideConfig[name] !== null) ? overrideConfig[name] : null));
        let theComponent = queryProp('component');
        let superType = queryProp('superType');
        let superDef = null;
        if (superType) {
            if (superType === viewType) {
                throw new Error('Can\'t have a custom view type that references itself');
            }
            superDef = ensureViewDef(superType, hash, defaultConfigs, overrideConfigs);
        }
        if (!theComponent && superDef) {
            theComponent = superDef.component;
        }
        if (!theComponent) {
            return null; // don't throw a warning, might be settings for a single-unit view
        }
        return {
            type: viewType,
            component: theComponent,
            defaults: Object.assign(Object.assign({}, (superDef ? superDef.defaults : {})), (defaultConfig ? defaultConfig.rawOptions : {})),
            overrides: Object.assign(Object.assign({}, (superDef ? superDef.overrides : {})), (overrideConfig ? overrideConfig.rawOptions : {})),
        };
    }

    function parseViewConfigs(inputs) {
        return mapHash(inputs, parseViewConfig);
    }
    function parseViewConfig(input) {
        let rawOptions = typeof input === 'function' ?
            { component: input } :
            input;
        let { component } = rawOptions;
        if (rawOptions.content) {
            // TODO: remove content/classNames/didMount/etc from options?
            component = createViewHookComponent(rawOptions);
        }
        else if (component && !(component.prototype instanceof BaseComponent)) {
            // WHY?: people were using `component` property for `content`
            // TODO: converge on one setting name
            component = createViewHookComponent(Object.assign(Object.assign({}, rawOptions), { content: component }));
        }
        return {
            superType: rawOptions.type,
            component: component,
            rawOptions, // includes type and component too :(
        };
    }
    function createViewHookComponent(options) {
        return (viewProps) => (y(ViewContextType.Consumer, null, (context) => (y(ContentContainer, { elTag: "div", elClasses: buildViewClassNames(context.viewSpec), renderProps: Object.assign(Object.assign({}, viewProps), { nextDayThreshold: context.options.nextDayThreshold }), generatorName: undefined, customGenerator: options.content, classNameGenerator: options.classNames, didMount: options.didMount, willUnmount: options.willUnmount }))));
    }

    function buildViewSpecs(defaultInputs, optionOverrides, dynamicOptionOverrides, localeDefaults) {
        let defaultConfigs = parseViewConfigs(defaultInputs);
        let overrideConfigs = parseViewConfigs(optionOverrides.views);
        let viewDefs = compileViewDefs(defaultConfigs, overrideConfigs);
        return mapHash(viewDefs, (viewDef) => buildViewSpec(viewDef, overrideConfigs, optionOverrides, dynamicOptionOverrides, localeDefaults));
    }
    function buildViewSpec(viewDef, overrideConfigs, optionOverrides, dynamicOptionOverrides, localeDefaults) {
        let durationInput = viewDef.overrides.duration ||
            viewDef.defaults.duration ||
            dynamicOptionOverrides.duration ||
            optionOverrides.duration;
        let duration = null;
        let durationUnit = '';
        let singleUnit = '';
        let singleUnitOverrides = {};
        if (durationInput) {
            duration = createDurationCached(durationInput);
            if (duration) { // valid?
                let denom = greatestDurationDenominator(duration);
                durationUnit = denom.unit;
                if (denom.value === 1) {
                    singleUnit = durationUnit;
                    singleUnitOverrides = overrideConfigs[durationUnit] ? overrideConfigs[durationUnit].rawOptions : {};
                }
            }
        }
        let queryButtonText = (optionsSubset) => {
            let buttonTextMap = optionsSubset.buttonText || {};
            let buttonTextKey = viewDef.defaults.buttonTextKey;
            if (buttonTextKey != null && buttonTextMap[buttonTextKey] != null) {
                return buttonTextMap[buttonTextKey];
            }
            if (buttonTextMap[viewDef.type] != null) {
                return buttonTextMap[viewDef.type];
            }
            if (buttonTextMap[singleUnit] != null) {
                return buttonTextMap[singleUnit];
            }
            return null;
        };
        let queryButtonTitle = (optionsSubset) => {
            let buttonHints = optionsSubset.buttonHints || {};
            let buttonKey = viewDef.defaults.buttonTextKey; // use same key as text
            if (buttonKey != null && buttonHints[buttonKey] != null) {
                return buttonHints[buttonKey];
            }
            if (buttonHints[viewDef.type] != null) {
                return buttonHints[viewDef.type];
            }
            if (buttonHints[singleUnit] != null) {
                return buttonHints[singleUnit];
            }
            return null;
        };
        return {
            type: viewDef.type,
            component: viewDef.component,
            duration,
            durationUnit,
            singleUnit,
            optionDefaults: viewDef.defaults,
            optionOverrides: Object.assign(Object.assign({}, singleUnitOverrides), viewDef.overrides),
            buttonTextOverride: queryButtonText(dynamicOptionOverrides) ||
                queryButtonText(optionOverrides) || // constructor-specified buttonText lookup hash takes precedence
                viewDef.overrides.buttonText,
            buttonTextDefault: queryButtonText(localeDefaults) ||
                viewDef.defaults.buttonText ||
                queryButtonText(BASE_OPTION_DEFAULTS) ||
                viewDef.type,
            // not DRY
            buttonTitleOverride: queryButtonTitle(dynamicOptionOverrides) ||
                queryButtonTitle(optionOverrides) ||
                viewDef.overrides.buttonHint,
            buttonTitleDefault: queryButtonTitle(localeDefaults) ||
                viewDef.defaults.buttonHint ||
                queryButtonTitle(BASE_OPTION_DEFAULTS),
            // will eventually fall back to buttonText
        };
    }
    // hack to get memoization working
    let durationInputMap = {};
    function createDurationCached(durationInput) {
        let json = JSON.stringify(durationInput);
        let res = durationInputMap[json];
        if (res === undefined) {
            res = createDuration(durationInput);
            durationInputMap[json] = res;
        }
        return res;
    }

    function reduceViewType(viewType, action) {
        switch (action.type) {
            case 'CHANGE_VIEW_TYPE':
                viewType = action.viewType;
        }
        return viewType;
    }

    function reduceCurrentDate(currentDate, action) {
        switch (action.type) {
            case 'CHANGE_DATE':
                return action.dateMarker;
            default:
                return currentDate;
        }
    }
    // should be initialized once and stay constant
    // this will change too
    function getInitialDate(options, dateEnv, nowManager) {
        let initialDateInput = options.initialDate;
        // compute the initial ambig-timezone date
        if (initialDateInput != null) {
            return dateEnv.createMarker(initialDateInput);
        }
        return nowManager.getDateMarker();
    }

    function reduceDynamicOptionOverrides(dynamicOptionOverrides, action) {
        switch (action.type) {
            case 'SET_OPTION':
                return Object.assign(Object.assign({}, dynamicOptionOverrides), { [action.optionName]: action.rawOptionValue });
            default:
                return dynamicOptionOverrides;
        }
    }

    function reduceDateProfile(currentDateProfile, action, currentDate, dateProfileGenerator) {
        let dp;
        switch (action.type) {
            case 'CHANGE_VIEW_TYPE':
                return dateProfileGenerator.build(action.dateMarker || currentDate);
            case 'CHANGE_DATE':
                return dateProfileGenerator.build(action.dateMarker);
            case 'PREV':
                dp = dateProfileGenerator.buildPrev(currentDateProfile, currentDate);
                if (dp.isValid) {
                    return dp;
                }
                break;
            case 'NEXT':
                dp = dateProfileGenerator.buildNext(currentDateProfile, currentDate);
                if (dp.isValid) {
                    return dp;
                }
                break;
        }
        return currentDateProfile;
    }

    function initEventSources(calendarOptions, dateProfile, context) {
        let activeRange = dateProfile ? dateProfile.activeRange : null;
        return addSources({}, parseInitialSources(calendarOptions, context), activeRange, context);
    }
    function reduceEventSources(eventSources, action, dateProfile, context) {
        let activeRange = dateProfile ? dateProfile.activeRange : null; // need this check?
        switch (action.type) {
            case 'ADD_EVENT_SOURCES': // already parsed
                return addSources(eventSources, action.sources, activeRange, context);
            case 'REMOVE_EVENT_SOURCE':
                return removeSource(eventSources, action.sourceId);
            case 'PREV': // TODO: how do we track all actions that affect dateProfile :(
            case 'NEXT':
            case 'CHANGE_DATE':
            case 'CHANGE_VIEW_TYPE':
                if (dateProfile) {
                    return fetchDirtySources(eventSources, activeRange, context);
                }
                return eventSources;
            case 'FETCH_EVENT_SOURCES':
                return fetchSourcesByIds(eventSources, action.sourceIds ? // why no type?
                    arrayToHash(action.sourceIds) :
                    excludeStaticSources(eventSources, context), activeRange, action.isRefetch || false, context);
            case 'RECEIVE_EVENTS':
            case 'RECEIVE_EVENT_ERROR':
                return receiveResponse(eventSources, action.sourceId, action.fetchId, action.fetchRange);
            case 'REMOVE_ALL_EVENT_SOURCES':
                return {};
            default:
                return eventSources;
        }
    }
    function reduceEventSourcesNewTimeZone(eventSources, dateProfile, context) {
        let activeRange = dateProfile ? dateProfile.activeRange : null; // need this check?
        return fetchSourcesByIds(eventSources, excludeStaticSources(eventSources, context), activeRange, true, context);
    }
    function computeEventSourcesLoading(eventSources) {
        for (let sourceId in eventSources) {
            if (eventSources[sourceId].isFetching) {
                return true;
            }
        }
        return false;
    }
    function addSources(eventSourceHash, sources, fetchRange, context) {
        let hash = {};
        for (let source of sources) {
            hash[source.sourceId] = source;
        }
        if (fetchRange) {
            hash = fetchDirtySources(hash, fetchRange, context);
        }
        return Object.assign(Object.assign({}, eventSourceHash), hash);
    }
    function removeSource(eventSourceHash, sourceId) {
        return filterHash(eventSourceHash, (eventSource) => eventSource.sourceId !== sourceId);
    }
    function fetchDirtySources(sourceHash, fetchRange, context) {
        return fetchSourcesByIds(sourceHash, filterHash(sourceHash, (eventSource) => isSourceDirty(eventSource, fetchRange, context)), fetchRange, false, context);
    }
    function isSourceDirty(eventSource, fetchRange, context) {
        if (!doesSourceNeedRange(eventSource, context)) {
            return !eventSource.latestFetchId;
        }
        return !context.options.lazyFetching ||
            !eventSource.fetchRange ||
            eventSource.isFetching || // always cancel outdated in-progress fetches
            fetchRange.start < eventSource.fetchRange.start ||
            fetchRange.end > eventSource.fetchRange.end;
    }
    function fetchSourcesByIds(prevSources, sourceIdHash, fetchRange, isRefetch, context) {
        let nextSources = {};
        for (let sourceId in prevSources) {
            let source = prevSources[sourceId];
            if (sourceIdHash[sourceId]) {
                nextSources[sourceId] = fetchSource(source, fetchRange, isRefetch, context);
            }
            else {
                nextSources[sourceId] = source;
            }
        }
        return nextSources;
    }
    function fetchSource(eventSource, fetchRange, isRefetch, context) {
        let { options, calendarApi } = context;
        let sourceDef = context.pluginHooks.eventSourceDefs[eventSource.sourceDefId];
        let fetchId = guid();
        sourceDef.fetch({
            eventSource,
            range: fetchRange,
            isRefetch,
            context,
        }, (res) => {
            let { rawEvents } = res;
            if (options.eventSourceSuccess) {
                rawEvents = options.eventSourceSuccess.call(calendarApi, rawEvents, res.response) || rawEvents;
            }
            if (eventSource.success) {
                rawEvents = eventSource.success.call(calendarApi, rawEvents, res.response) || rawEvents;
            }
            context.dispatch({
                type: 'RECEIVE_EVENTS',
                sourceId: eventSource.sourceId,
                fetchId,
                fetchRange,
                rawEvents,
            });
        }, (error) => {
            let errorHandled = false;
            if (options.eventSourceFailure) {
                options.eventSourceFailure.call(calendarApi, error);
                errorHandled = true;
            }
            if (eventSource.failure) {
                eventSource.failure(error);
                errorHandled = true;
            }
            if (!errorHandled) {
                console.warn(error.message, error);
            }
            context.dispatch({
                type: 'RECEIVE_EVENT_ERROR',
                sourceId: eventSource.sourceId,
                fetchId,
                fetchRange,
                error,
            });
        });
        return Object.assign(Object.assign({}, eventSource), { isFetching: true, latestFetchId: fetchId });
    }
    function receiveResponse(sourceHash, sourceId, fetchId, fetchRange) {
        let eventSource = sourceHash[sourceId];
        if (eventSource && // not already removed
            fetchId === eventSource.latestFetchId) {
            return Object.assign(Object.assign({}, sourceHash), { [sourceId]: Object.assign(Object.assign({}, eventSource), { isFetching: false, fetchRange }) });
        }
        return sourceHash;
    }
    function excludeStaticSources(eventSources, context) {
        return filterHash(eventSources, (eventSource) => doesSourceNeedRange(eventSource, context));
    }
    function parseInitialSources(rawOptions, context) {
        let refiners = buildEventSourceRefiners(context);
        let rawSources = [].concat(rawOptions.eventSources || []);
        let sources = []; // parsed
        if (rawOptions.initialEvents) {
            rawSources.unshift(rawOptions.initialEvents);
        }
        if (rawOptions.events) {
            rawSources.unshift(rawOptions.events);
        }
        for (let rawSource of rawSources) {
            let source = parseEventSource(rawSource, context, refiners);
            if (source) {
                sources.push(source);
            }
        }
        return sources;
    }
    function doesSourceNeedRange(eventSource, context) {
        let defs = context.pluginHooks.eventSourceDefs;
        return !defs[eventSource.sourceDefId].ignoreRange;
    }

    function reduceDateSelection(currentSelection, action) {
        switch (action.type) {
            case 'UNSELECT_DATES':
                return null;
            case 'SELECT_DATES':
                return action.selection;
            default:
                return currentSelection;
        }
    }

    function reduceSelectedEvent(currentInstanceId, action) {
        switch (action.type) {
            case 'UNSELECT_EVENT':
                return '';
            case 'SELECT_EVENT':
                return action.eventInstanceId;
            default:
                return currentInstanceId;
        }
    }

    function reduceEventDrag(currentDrag, action) {
        let newDrag;
        switch (action.type) {
            case 'UNSET_EVENT_DRAG':
                return null;
            case 'SET_EVENT_DRAG':
                newDrag = action.state;
                return {
                    affectedEvents: newDrag.affectedEvents,
                    mutatedEvents: newDrag.mutatedEvents,
                    isEvent: newDrag.isEvent,
                };
            default:
                return currentDrag;
        }
    }

    function reduceEventResize(currentResize, action) {
        let newResize;
        switch (action.type) {
            case 'UNSET_EVENT_RESIZE':
                return null;
            case 'SET_EVENT_RESIZE':
                newResize = action.state;
                return {
                    affectedEvents: newResize.affectedEvents,
                    mutatedEvents: newResize.mutatedEvents,
                    isEvent: newResize.isEvent,
                };
            default:
                return currentResize;
        }
    }

    function parseToolbars(calendarOptions, calendarOptionOverrides, theme, viewSpecs, calendarApi) {
        let header = calendarOptions.headerToolbar ? parseToolbar(calendarOptions.headerToolbar, calendarOptions, calendarOptionOverrides, theme, viewSpecs, calendarApi) : null;
        let footer = calendarOptions.footerToolbar ? parseToolbar(calendarOptions.footerToolbar, calendarOptions, calendarOptionOverrides, theme, viewSpecs, calendarApi) : null;
        return { header, footer };
    }
    function parseToolbar(sectionStrHash, calendarOptions, calendarOptionOverrides, theme, viewSpecs, calendarApi) {
        let sectionWidgets = {};
        let viewsWithButtons = [];
        let hasTitle = false;
        for (let sectionName in sectionStrHash) {
            let sectionStr = sectionStrHash[sectionName];
            let sectionRes = parseSection(sectionStr, calendarOptions, calendarOptionOverrides, theme, viewSpecs, calendarApi);
            sectionWidgets[sectionName] = sectionRes.widgets;
            viewsWithButtons.push(...sectionRes.viewsWithButtons);
            hasTitle = hasTitle || sectionRes.hasTitle;
        }
        return { sectionWidgets, viewsWithButtons, hasTitle };
    }
    /*
    BAD: querying icons and text here. should be done at render time
    */
    function parseSection(sectionStr, calendarOptions, // defaults+overrides, then refined
    calendarOptionOverrides, // overrides only!, unrefined :(
    theme, viewSpecs, calendarApi) {
        let isRtl = calendarOptions.direction === 'rtl';
        let calendarCustomButtons = calendarOptions.customButtons || {};
        let calendarButtonTextOverrides = calendarOptionOverrides.buttonText || {};
        let calendarButtonText = calendarOptions.buttonText || {};
        let calendarButtonHintOverrides = calendarOptionOverrides.buttonHints || {};
        let calendarButtonHints = calendarOptions.buttonHints || {};
        let sectionSubstrs = sectionStr ? sectionStr.split(' ') : [];
        let viewsWithButtons = [];
        let hasTitle = false;
        let widgets = sectionSubstrs.map((buttonGroupStr) => (buttonGroupStr.split(',').map((buttonName) => {
            if (buttonName === 'title') {
                hasTitle = true;
                return { buttonName };
            }
            let customButtonProps;
            let viewSpec;
            let buttonClick;
            let buttonIcon; // only one of these will be set
            let buttonText; // "
            let buttonHint;
            // ^ for the title="" attribute, for accessibility
            if ((customButtonProps = calendarCustomButtons[buttonName])) {
                buttonClick = (ev) => {
                    if (customButtonProps.click) {
                        customButtonProps.click.call(ev.target, ev, ev.target); // TODO: use Calendar this context?
                    }
                };
                (buttonIcon = theme.getCustomButtonIconClass(customButtonProps)) ||
                    (buttonIcon = theme.getIconClass(buttonName, isRtl)) ||
                    (buttonText = customButtonProps.text);
                buttonHint = customButtonProps.hint || customButtonProps.text;
            }
            else if ((viewSpec = viewSpecs[buttonName])) {
                viewsWithButtons.push(buttonName);
                buttonClick = () => {
                    calendarApi.changeView(buttonName);
                };
                (buttonText = viewSpec.buttonTextOverride) ||
                    (buttonIcon = theme.getIconClass(buttonName, isRtl)) ||
                    (buttonText = viewSpec.buttonTextDefault);
                let textFallback = viewSpec.buttonTextOverride ||
                    viewSpec.buttonTextDefault;
                buttonHint = formatWithOrdinals(viewSpec.buttonTitleOverride ||
                    viewSpec.buttonTitleDefault ||
                    calendarOptions.viewHint, [textFallback, buttonName], // view-name = buttonName
                textFallback);
            }
            else if (calendarApi[buttonName]) { // a calendarApi method
                buttonClick = () => {
                    calendarApi[buttonName]();
                };
                (buttonText = calendarButtonTextOverrides[buttonName]) ||
                    (buttonIcon = theme.getIconClass(buttonName, isRtl)) ||
                    (buttonText = calendarButtonText[buttonName]); // everything else is considered default
                if (buttonName === 'prevYear' || buttonName === 'nextYear') {
                    let prevOrNext = buttonName === 'prevYear' ? 'prev' : 'next';
                    buttonHint = formatWithOrdinals(calendarButtonHintOverrides[prevOrNext] ||
                        calendarButtonHints[prevOrNext], [
                        calendarButtonText.year || 'year',
                        'year',
                    ], calendarButtonText[buttonName]);
                }
                else {
                    buttonHint = (navUnit) => formatWithOrdinals(calendarButtonHintOverrides[buttonName] ||
                        calendarButtonHints[buttonName], [
                        calendarButtonText[navUnit] || navUnit,
                        navUnit,
                    ], calendarButtonText[buttonName]);
                }
            }
            return { buttonName, buttonClick, buttonIcon, buttonText, buttonHint };
        })));
        return { widgets, viewsWithButtons, hasTitle };
    }

    // always represents the current view. otherwise, it'd need to change value every time date changes
    class ViewImpl {
        constructor(type, getCurrentData, dateEnv) {
            this.type = type;
            this.getCurrentData = getCurrentData;
            this.dateEnv = dateEnv;
        }
        get calendar() {
            return this.getCurrentData().calendarApi;
        }
        get title() {
            return this.getCurrentData().viewTitle;
        }
        get activeStart() {
            return this.dateEnv.toDate(this.getCurrentData().dateProfile.activeRange.start);
        }
        get activeEnd() {
            return this.dateEnv.toDate(this.getCurrentData().dateProfile.activeRange.end);
        }
        get currentStart() {
            return this.dateEnv.toDate(this.getCurrentData().dateProfile.currentRange.start);
        }
        get currentEnd() {
            return this.dateEnv.toDate(this.getCurrentData().dateProfile.currentRange.end);
        }
        getOption(name) {
            return this.getCurrentData().options[name]; // are the view-specific options
        }
    }

    let eventSourceDef$2 = {
        ignoreRange: true,
        parseMeta(refined) {
            if (Array.isArray(refined.events)) {
                return refined.events;
            }
            return null;
        },
        fetch(arg, successCallback) {
            successCallback({
                rawEvents: arg.eventSource.meta,
            });
        },
    };
    const arrayEventSourcePlugin = createPlugin({
        name: 'array-event-source',
        eventSourceDefs: [eventSourceDef$2],
    });

    let eventSourceDef$1 = {
        parseMeta(refined) {
            if (typeof refined.events === 'function') {
                return refined.events;
            }
            return null;
        },
        fetch(arg, successCallback, errorCallback) {
            const { dateEnv } = arg.context;
            const func = arg.eventSource.meta;
            unpromisify(func.bind(null, buildRangeApiWithTimeZone(arg.range, dateEnv)), (rawEvents) => successCallback({ rawEvents }), errorCallback);
        },
    };
    const funcEventSourcePlugin = createPlugin({
        name: 'func-event-source',
        eventSourceDefs: [eventSourceDef$1],
    });

    const JSON_FEED_EVENT_SOURCE_REFINERS = {
        method: String,
        extraParams: identity,
        startParam: String,
        endParam: String,
        timeZoneParam: String,
    };

    let eventSourceDef = {
        parseMeta(refined) {
            if (refined.url && (refined.format === 'json' || !refined.format)) {
                return {
                    url: refined.url,
                    format: 'json',
                    method: (refined.method || 'GET').toUpperCase(),
                    extraParams: refined.extraParams,
                    startParam: refined.startParam,
                    endParam: refined.endParam,
                    timeZoneParam: refined.timeZoneParam,
                };
            }
            return null;
        },
        fetch(arg, successCallback, errorCallback) {
            const { meta } = arg.eventSource;
            const requestParams = buildRequestParams(meta, arg.range, arg.context);
            requestJson(meta.method, meta.url, requestParams).then(([rawEvents, response]) => {
                successCallback({ rawEvents, response });
            }, errorCallback);
        },
    };
    const jsonFeedEventSourcePlugin = createPlugin({
        name: 'json-event-source',
        eventSourceRefiners: JSON_FEED_EVENT_SOURCE_REFINERS,
        eventSourceDefs: [eventSourceDef],
    });
    function buildRequestParams(meta, range, context) {
        let { dateEnv, options } = context;
        let startParam;
        let endParam;
        let timeZoneParam;
        let customRequestParams;
        let params = {};
        startParam = meta.startParam;
        if (startParam == null) {
            startParam = options.startParam;
        }
        endParam = meta.endParam;
        if (endParam == null) {
            endParam = options.endParam;
        }
        timeZoneParam = meta.timeZoneParam;
        if (timeZoneParam == null) {
            timeZoneParam = options.timeZoneParam;
        }
        // retrieve any outbound GET/POST data from the options
        if (typeof meta.extraParams === 'function') {
            // supplied as a function that returns a key/value object
            customRequestParams = meta.extraParams();
        }
        else {
            // probably supplied as a straight key/value object
            customRequestParams = meta.extraParams || {};
        }
        Object.assign(params, customRequestParams);
        params[startParam] = dateEnv.formatIso(range.start);
        params[endParam] = dateEnv.formatIso(range.end);
        if (dateEnv.timeZone !== 'local') {
            params[timeZoneParam] = dateEnv.timeZone;
        }
        return params;
    }

    const SIMPLE_RECURRING_REFINERS = {
        daysOfWeek: identity,
        startTime: createDuration,
        endTime: createDuration,
        duration: createDuration,
        startRecur: identity,
        endRecur: identity,
    };

    let recurring = {
        parse(refined, dateEnv) {
            if (refined.daysOfWeek || refined.startTime || refined.endTime || refined.startRecur || refined.endRecur) {
                let recurringData = {
                    daysOfWeek: refined.daysOfWeek || null,
                    startTime: refined.startTime || null,
                    endTime: refined.endTime || null,
                    startRecur: refined.startRecur ? dateEnv.createMarker(refined.startRecur) : null,
                    endRecur: refined.endRecur ? dateEnv.createMarker(refined.endRecur) : null,
                    dateEnv,
                };
                let duration;
                if (refined.duration) {
                    duration = refined.duration;
                }
                if (!duration && refined.startTime && refined.endTime) {
                    duration = subtractDurations(refined.endTime, refined.startTime);
                }
                return {
                    allDayGuess: Boolean(!refined.startTime && !refined.endTime),
                    duration,
                    typeData: recurringData, // doesn't need endTime anymore but oh well
                };
            }
            return null;
        },
        expand(typeData, framingRange, dateEnv) {
            let clippedFramingRange = intersectRanges(framingRange, { start: typeData.startRecur, end: typeData.endRecur });
            if (clippedFramingRange) {
                return expandRanges(typeData.daysOfWeek, typeData.startTime, typeData.dateEnv, dateEnv, clippedFramingRange);
            }
            return [];
        },
    };
    const simpleRecurringEventsPlugin = createPlugin({
        name: 'simple-recurring-event',
        recurringTypes: [recurring],
        eventRefiners: SIMPLE_RECURRING_REFINERS,
    });
    function expandRanges(daysOfWeek, startTime, eventDateEnv, calendarDateEnv, framingRange) {
        let dowHash = daysOfWeek ? arrayToHash(daysOfWeek) : null;
        let dayMarker = startOfDay(framingRange.start);
        let endMarker = framingRange.end;
        let instanceStarts = [];
        // https://github.com/fullcalendar/fullcalendar/issues/7934
        if (startTime) {
            if (startTime.milliseconds < 0) {
                // possible for next-day to have negative business hours that go into current day
                endMarker = addDays(endMarker, 1);
            }
            else if (startTime.milliseconds >= 1000 * 60 * 60 * 24) {
                // possible for prev-day to have >24hr business hours that go into current day
                dayMarker = addDays(dayMarker, -1);
            }
        }
        while (dayMarker < endMarker) {
            let instanceStart;
            // if everyday, or this particular day-of-week
            if (!dowHash || dowHash[dayMarker.getUTCDay()]) {
                if (startTime) {
                    instanceStart = calendarDateEnv.add(dayMarker, startTime);
                }
                else {
                    instanceStart = dayMarker;
                }
                instanceStarts.push(calendarDateEnv.createMarker(eventDateEnv.toDate(instanceStart)));
            }
            dayMarker = addDays(dayMarker, 1);
        }
        return instanceStarts;
    }

    const changeHandlerPlugin = createPlugin({
        name: 'change-handler',
        optionChangeHandlers: {
            events(events, context) {
                handleEventSources([events], context);
            },
            eventSources: handleEventSources,
        },
    });
    /*
    BUG: if `event` was supplied, all previously-given `eventSources` will be wiped out
    */
    function handleEventSources(inputs, context) {
        let unfoundSources = hashValuesToArray(context.getCurrentData().eventSources);
        if (unfoundSources.length === 1 &&
            inputs.length === 1 &&
            Array.isArray(unfoundSources[0]._raw) &&
            Array.isArray(inputs[0])) {
            context.dispatch({
                type: 'RESET_RAW_EVENTS',
                sourceId: unfoundSources[0].sourceId,
                rawEvents: inputs[0],
            });
            return;
        }
        let newInputs = [];
        for (let input of inputs) {
            let inputFound = false;
            for (let i = 0; i < unfoundSources.length; i += 1) {
                if (unfoundSources[i]._raw === input) {
                    unfoundSources.splice(i, 1); // delete
                    inputFound = true;
                    break;
                }
            }
            if (!inputFound) {
                newInputs.push(input);
            }
        }
        for (let unfoundSource of unfoundSources) {
            context.dispatch({
                type: 'REMOVE_EVENT_SOURCE',
                sourceId: unfoundSource.sourceId,
            });
        }
        for (let newInput of newInputs) {
            context.calendarApi.addEventSource(newInput);
        }
    }

    function handleDateProfile(dateProfile, context) {
        context.emitter.trigger('datesSet', Object.assign(Object.assign({}, buildRangeApiWithTimeZone(dateProfile.activeRange, context.dateEnv)), { view: context.viewApi }));
    }

    function handleEventStore(eventStore, context) {
        let { emitter } = context;
        if (emitter.hasHandlers('eventsSet')) {
            emitter.trigger('eventsSet', buildEventApis(eventStore, context));
        }
    }

    /*
    this array is exposed on the root namespace so that UMD plugins can add to it.
    see the rollup-bundles script.
    */
    const globalPlugins = [
        arrayEventSourcePlugin,
        funcEventSourcePlugin,
        jsonFeedEventSourcePlugin,
        simpleRecurringEventsPlugin,
        changeHandlerPlugin,
        createPlugin({
            name: 'misc',
            isLoadingFuncs: [
                (state) => computeEventSourcesLoading(state.eventSources),
            ],
            propSetHandlers: {
                dateProfile: handleDateProfile,
                eventStore: handleEventStore,
            },
        }),
    ];

    class TaskRunner {
        constructor(runTaskOption, drainedOption) {
            this.runTaskOption = runTaskOption;
            this.drainedOption = drainedOption;
            this.queue = [];
            this.delayedRunner = new DelayedRunner(this.drain.bind(this));
        }
        request(task, delay) {
            this.queue.push(task);
            this.delayedRunner.request(delay);
        }
        pause(scope) {
            this.delayedRunner.pause(scope);
        }
        resume(scope, force) {
            this.delayedRunner.resume(scope, force);
        }
        drain() {
            let { queue } = this;
            while (queue.length) {
                let completedTasks = [];
                let task;
                while ((task = queue.shift())) {
                    this.runTask(task);
                    completedTasks.push(task);
                }
                this.drained(completedTasks);
            } // keep going, in case new tasks were added in the drained handler
        }
        runTask(task) {
            if (this.runTaskOption) {
                this.runTaskOption(task);
            }
        }
        drained(completedTasks) {
            if (this.drainedOption) {
                this.drainedOption(completedTasks);
            }
        }
    }

    // Computes what the title at the top of the calendarApi should be for this view
    function buildTitle(dateProfile, viewOptions, dateEnv) {
        let range;
        // for views that span a large unit of time, show the proper interval, ignoring stray days before and after
        if (/^(year|month)$/.test(dateProfile.currentRangeUnit)) {
            range = dateProfile.currentRange;
        }
        else { // for day units or smaller, use the actual day range
            range = dateProfile.activeRange;
        }
        return dateEnv.formatRange(range.start, range.end, createFormatter(viewOptions.titleFormat || buildTitleFormat(dateProfile)), {
            isEndExclusive: dateProfile.isRangeAllDay,
            defaultSeparator: viewOptions.titleRangeSeparator,
        });
    }
    // Generates the format string that should be used to generate the title for the current date range.
    // Attempts to compute the most appropriate format if not explicitly specified with `titleFormat`.
    function buildTitleFormat(dateProfile) {
        let { currentRangeUnit } = dateProfile;
        if (currentRangeUnit === 'year') {
            return { year: 'numeric' };
        }
        if (currentRangeUnit === 'month') {
            return { year: 'numeric', month: 'long' }; // like "September 2014"
        }
        let days = diffWholeDays(dateProfile.currentRange.start, dateProfile.currentRange.end);
        if (days !== null && days > 1) {
            // multi-day range. shorter, like "Sep 9 - 10 2014"
            return { year: 'numeric', month: 'short', day: 'numeric' };
        }
        // one day. longer, like "September 9 2014"
        return { year: 'numeric', month: 'long', day: 'numeric' };
    }

    /*
    TODO: test switching timezones when NO timezone plugin
    */
    class CalendarNowManager {
        constructor() {
            this.resetListeners = new Set();
        }
        handleInput(dateEnv, // will change if timezone setup changed
        nowInput) {
            const oldDateEnv = this.dateEnv;
            if (dateEnv !== oldDateEnv) {
                if (typeof nowInput === 'function') {
                    this.nowFn = nowInput;
                }
                else if (!oldDateEnv) { // first time?
                    this.nowAnchorDate = dateEnv.toDate(nowInput
                        ? dateEnv.createMarker(nowInput)
                        : dateEnv.createNowMarker());
                    this.nowAnchorQueried = Date.now();
                }
                this.dateEnv = dateEnv;
                // not first time? fire reset handlers
                if (oldDateEnv) {
                    for (const resetListener of this.resetListeners.values()) {
                        resetListener();
                    }
                }
            }
        }
        getDateMarker() {
            return this.nowAnchorDate
                ? this.dateEnv.timestampToMarker(this.nowAnchorDate.valueOf() +
                    (Date.now() - this.nowAnchorQueried))
                : this.dateEnv.createMarker(this.nowFn());
        }
        addResetListener(handler) {
            this.resetListeners.add(handler);
        }
        removeResetListener(handler) {
            this.resetListeners.delete(handler);
        }
    }

    // in future refactor, do the redux-style function(state=initial) for initial-state
    // also, whatever is happening in constructor, have it happen in action queue too
    class CalendarDataManager {
        constructor(props) {
            this.computeCurrentViewData = memoize(this._computeCurrentViewData);
            this.organizeRawLocales = memoize(organizeRawLocales);
            this.buildLocale = memoize(buildLocale);
            this.buildPluginHooks = buildBuildPluginHooks();
            this.buildDateEnv = memoize(buildDateEnv$1);
            this.buildTheme = memoize(buildTheme);
            this.parseToolbars = memoize(parseToolbars);
            this.buildViewSpecs = memoize(buildViewSpecs);
            this.buildDateProfileGenerator = memoizeObjArg(buildDateProfileGenerator);
            this.buildViewApi = memoize(buildViewApi);
            this.buildViewUiProps = memoizeObjArg(buildViewUiProps);
            this.buildEventUiBySource = memoize(buildEventUiBySource, isPropsEqual);
            this.buildEventUiBases = memoize(buildEventUiBases);
            this.parseContextBusinessHours = memoizeObjArg(parseContextBusinessHours);
            this.buildTitle = memoize(buildTitle);
            this.nowManager = new CalendarNowManager();
            this.emitter = new Emitter();
            this.actionRunner = new TaskRunner(this._handleAction.bind(this), this.updateData.bind(this));
            this.currentCalendarOptionsInput = {};
            this.currentCalendarOptionsRefined = {};
            this.currentViewOptionsInput = {};
            this.currentViewOptionsRefined = {};
            this.currentCalendarOptionsRefiners = {};
            this.optionsForRefining = [];
            this.optionsForHandling = [];
            this.getCurrentData = () => this.data;
            this.dispatch = (action) => {
                this.actionRunner.request(action); // protects against recursive calls to _handleAction
            };
            this.props = props;
            this.actionRunner.pause();
            this.nowManager = new CalendarNowManager();
            let dynamicOptionOverrides = {};
            let optionsData = this.computeOptionsData(props.optionOverrides, dynamicOptionOverrides, props.calendarApi);
            let currentViewType = optionsData.calendarOptions.initialView || optionsData.pluginHooks.initialView;
            let currentViewData = this.computeCurrentViewData(currentViewType, optionsData, props.optionOverrides, dynamicOptionOverrides);
            // wire things up
            // TODO: not DRY
            props.calendarApi.currentDataManager = this;
            this.emitter.setThisContext(props.calendarApi);
            this.emitter.setOptions(currentViewData.options);
            let calendarContext = {
                nowManager: this.nowManager,
                dateEnv: optionsData.dateEnv,
                options: optionsData.calendarOptions,
                pluginHooks: optionsData.pluginHooks,
                calendarApi: props.calendarApi,
                dispatch: this.dispatch,
                emitter: this.emitter,
                getCurrentData: this.getCurrentData,
            };
            let currentDate = getInitialDate(optionsData.calendarOptions, optionsData.dateEnv, this.nowManager);
            let dateProfile = currentViewData.dateProfileGenerator.build(currentDate);
            if (!rangeContainsMarker(dateProfile.activeRange, currentDate)) {
                currentDate = dateProfile.currentRange.start;
            }
            // needs to be after setThisContext
            for (let callback of optionsData.pluginHooks.contextInit) {
                callback(calendarContext);
            }
            // NOT DRY
            let eventSources = initEventSources(optionsData.calendarOptions, dateProfile, calendarContext);
            let initialState = {
                dynamicOptionOverrides,
                currentViewType,
                currentDate,
                dateProfile,
                businessHours: this.parseContextBusinessHours(calendarContext),
                eventSources,
                eventUiBases: {},
                eventStore: createEmptyEventStore(),
                renderableEventStore: createEmptyEventStore(),
                dateSelection: null,
                eventSelection: '',
                eventDrag: null,
                eventResize: null,
                selectionConfig: this.buildViewUiProps(calendarContext).selectionConfig,
            };
            let contextAndState = Object.assign(Object.assign({}, calendarContext), initialState);
            for (let reducer of optionsData.pluginHooks.reducers) {
                Object.assign(initialState, reducer(null, null, contextAndState));
            }
            if (computeIsLoading(initialState, calendarContext)) {
                this.emitter.trigger('loading', true); // NOT DRY
            }
            this.state = initialState;
            this.updateData();
            this.actionRunner.resume();
        }
        resetOptions(optionOverrides, changedOptionNames) {
            let { props } = this;
            if (changedOptionNames === undefined) {
                props.optionOverrides = optionOverrides;
            }
            else {
                props.optionOverrides = Object.assign(Object.assign({}, (props.optionOverrides || {})), optionOverrides);
                this.optionsForRefining.push(...changedOptionNames);
            }
            if (changedOptionNames === undefined || changedOptionNames.length) {
                this.actionRunner.request({
                    type: 'NOTHING',
                });
            }
        }
        _handleAction(action) {
            let { props, state, emitter } = this;
            let dynamicOptionOverrides = reduceDynamicOptionOverrides(state.dynamicOptionOverrides, action);
            let optionsData = this.computeOptionsData(props.optionOverrides, dynamicOptionOverrides, props.calendarApi);
            let currentViewType = reduceViewType(state.currentViewType, action);
            let currentViewData = this.computeCurrentViewData(currentViewType, optionsData, props.optionOverrides, dynamicOptionOverrides);
            // wire things up
            // TODO: not DRY
            props.calendarApi.currentDataManager = this;
            emitter.setThisContext(props.calendarApi);
            emitter.setOptions(currentViewData.options);
            let calendarContext = {
                nowManager: this.nowManager,
                dateEnv: optionsData.dateEnv,
                options: optionsData.calendarOptions,
                pluginHooks: optionsData.pluginHooks,
                calendarApi: props.calendarApi,
                dispatch: this.dispatch,
                emitter,
                getCurrentData: this.getCurrentData,
            };
            let { currentDate, dateProfile } = state;
            if (this.data && this.data.dateProfileGenerator !== currentViewData.dateProfileGenerator) { // hack
                dateProfile = currentViewData.dateProfileGenerator.build(currentDate);
            }
            currentDate = reduceCurrentDate(currentDate, action);
            dateProfile = reduceDateProfile(dateProfile, action, currentDate, currentViewData.dateProfileGenerator);
            if (action.type === 'PREV' || // TODO: move this logic into DateProfileGenerator
                action.type === 'NEXT' || // "
                !rangeContainsMarker(dateProfile.currentRange, currentDate)) {
                currentDate = dateProfile.currentRange.start;
            }
            let eventSources = reduceEventSources(state.eventSources, action, dateProfile, calendarContext);
            let eventStore = reduceEventStore(state.eventStore, action, eventSources, dateProfile, calendarContext);
            let isEventsLoading = computeEventSourcesLoading(eventSources); // BAD. also called in this func in computeIsLoading
            let renderableEventStore = (isEventsLoading && !currentViewData.options.progressiveEventRendering) ?
                (state.renderableEventStore || eventStore) : // try from previous state
                eventStore;
            let { eventUiSingleBase, selectionConfig } = this.buildViewUiProps(calendarContext); // will memoize obj
            let eventUiBySource = this.buildEventUiBySource(eventSources);
            let eventUiBases = this.buildEventUiBases(renderableEventStore.defs, eventUiSingleBase, eventUiBySource);
            let newState = {
                dynamicOptionOverrides,
                currentViewType,
                currentDate,
                dateProfile,
                eventSources,
                eventStore,
                renderableEventStore,
                selectionConfig,
                eventUiBases,
                businessHours: this.parseContextBusinessHours(calendarContext),
                dateSelection: reduceDateSelection(state.dateSelection, action),
                eventSelection: reduceSelectedEvent(state.eventSelection, action),
                eventDrag: reduceEventDrag(state.eventDrag, action),
                eventResize: reduceEventResize(state.eventResize, action),
            };
            let contextAndState = Object.assign(Object.assign({}, calendarContext), newState);
            for (let reducer of optionsData.pluginHooks.reducers) {
                Object.assign(newState, reducer(state, action, contextAndState)); // give the OLD state, for old value
            }
            let wasLoading = computeIsLoading(state, calendarContext);
            let isLoading = computeIsLoading(newState, calendarContext);
            // TODO: use propSetHandlers in plugin system
            if (!wasLoading && isLoading) {
                emitter.trigger('loading', true);
            }
            else if (wasLoading && !isLoading) {
                emitter.trigger('loading', false);
            }
            this.state = newState;
            if (props.onAction) {
                props.onAction(action);
            }
        }
        updateData() {
            let { props, state } = this;
            let oldData = this.data;
            let optionsData = this.computeOptionsData(props.optionOverrides, state.dynamicOptionOverrides, props.calendarApi);
            let currentViewData = this.computeCurrentViewData(state.currentViewType, optionsData, props.optionOverrides, state.dynamicOptionOverrides);
            let data = this.data = Object.assign(Object.assign(Object.assign({ nowManager: this.nowManager, viewTitle: this.buildTitle(state.dateProfile, currentViewData.options, optionsData.dateEnv), calendarApi: props.calendarApi, dispatch: this.dispatch, emitter: this.emitter, getCurrentData: this.getCurrentData }, optionsData), currentViewData), state);
            let changeHandlers = optionsData.pluginHooks.optionChangeHandlers;
            let oldCalendarOptions = oldData && oldData.calendarOptions;
            let newCalendarOptions = optionsData.calendarOptions;
            if (oldCalendarOptions && oldCalendarOptions !== newCalendarOptions) {
                if (oldCalendarOptions.timeZone !== newCalendarOptions.timeZone) {
                    // hack
                    state.eventSources = data.eventSources = reduceEventSourcesNewTimeZone(data.eventSources, state.dateProfile, data);
                    state.eventStore = data.eventStore = rezoneEventStoreDates(data.eventStore, oldData.dateEnv, data.dateEnv);
                    state.renderableEventStore = data.renderableEventStore = rezoneEventStoreDates(data.renderableEventStore, oldData.dateEnv, data.dateEnv);
                }
                for (let optionName in changeHandlers) {
                    if (this.optionsForHandling.indexOf(optionName) !== -1 ||
                        oldCalendarOptions[optionName] !== newCalendarOptions[optionName]) {
                        changeHandlers[optionName](newCalendarOptions[optionName], data);
                    }
                }
            }
            this.optionsForHandling = [];
            if (props.onData) {
                props.onData(data);
            }
        }
        computeOptionsData(optionOverrides, dynamicOptionOverrides, calendarApi) {
            // TODO: blacklist options that are handled by optionChangeHandlers
            if (!this.optionsForRefining.length &&
                optionOverrides === this.stableOptionOverrides &&
                dynamicOptionOverrides === this.stableDynamicOptionOverrides) {
                return this.stableCalendarOptionsData;
            }
            let { refinedOptions, pluginHooks, localeDefaults, availableLocaleData, extra, } = this.processRawCalendarOptions(optionOverrides, dynamicOptionOverrides);
            warnUnknownOptions(extra);
            let dateEnv = this.buildDateEnv(refinedOptions.timeZone, refinedOptions.locale, refinedOptions.weekNumberCalculation, refinedOptions.firstDay, refinedOptions.weekText, pluginHooks, availableLocaleData, refinedOptions.defaultRangeSeparator);
            let viewSpecs = this.buildViewSpecs(pluginHooks.views, this.stableOptionOverrides, this.stableDynamicOptionOverrides, localeDefaults);
            let theme = this.buildTheme(refinedOptions, pluginHooks);
            let toolbarConfig = this.parseToolbars(refinedOptions, this.stableOptionOverrides, theme, viewSpecs, calendarApi);
            return this.stableCalendarOptionsData = {
                calendarOptions: refinedOptions,
                pluginHooks,
                dateEnv,
                viewSpecs,
                theme,
                toolbarConfig,
                localeDefaults,
                availableRawLocales: availableLocaleData.map,
            };
        }
        // always called from behind a memoizer
        processRawCalendarOptions(optionOverrides, dynamicOptionOverrides) {
            let { locales, locale } = mergeRawOptions([
                BASE_OPTION_DEFAULTS,
                optionOverrides,
                dynamicOptionOverrides,
            ]);
            let availableLocaleData = this.organizeRawLocales(locales);
            let availableRawLocales = availableLocaleData.map;
            let localeDefaults = this.buildLocale(locale || availableLocaleData.defaultCode, availableRawLocales).options;
            let pluginHooks = this.buildPluginHooks(optionOverrides.plugins || [], globalPlugins);
            let refiners = this.currentCalendarOptionsRefiners = Object.assign(Object.assign(Object.assign(Object.assign(Object.assign({}, BASE_OPTION_REFINERS), CALENDAR_LISTENER_REFINERS), CALENDAR_OPTION_REFINERS), pluginHooks.listenerRefiners), pluginHooks.optionRefiners);
            let extra = {};
            let raw = mergeRawOptions([
                BASE_OPTION_DEFAULTS,
                localeDefaults,
                optionOverrides,
                dynamicOptionOverrides,
            ]);
            let refined = {};
            let currentRaw = this.currentCalendarOptionsInput;
            let currentRefined = this.currentCalendarOptionsRefined;
            let anyChanges = false;
            for (let optionName in raw) {
                if (this.optionsForRefining.indexOf(optionName) === -1 && (raw[optionName] === currentRaw[optionName] || (COMPLEX_OPTION_COMPARATORS[optionName] &&
                    (optionName in currentRaw) &&
                    COMPLEX_OPTION_COMPARATORS[optionName](currentRaw[optionName], raw[optionName])))) {
                    refined[optionName] = currentRefined[optionName];
                }
                else if (refiners[optionName]) {
                    refined[optionName] = refiners[optionName](raw[optionName]);
                    anyChanges = true;
                }
                else {
                    extra[optionName] = currentRaw[optionName];
                }
            }
            if (anyChanges) {
                this.currentCalendarOptionsInput = raw;
                this.currentCalendarOptionsRefined = refined;
                this.stableOptionOverrides = optionOverrides;
                this.stableDynamicOptionOverrides = dynamicOptionOverrides;
            }
            this.optionsForHandling.push(...this.optionsForRefining);
            this.optionsForRefining = [];
            return {
                rawOptions: this.currentCalendarOptionsInput,
                refinedOptions: this.currentCalendarOptionsRefined,
                pluginHooks,
                availableLocaleData,
                localeDefaults,
                extra,
            };
        }
        _computeCurrentViewData(viewType, optionsData, optionOverrides, dynamicOptionOverrides) {
            let viewSpec = optionsData.viewSpecs[viewType];
            if (!viewSpec) {
                throw new Error(`viewType "${viewType}" is not available. Please make sure you've loaded all neccessary plugins`);
            }
            let { refinedOptions, extra } = this.processRawViewOptions(viewSpec, optionsData.pluginHooks, optionsData.localeDefaults, optionOverrides, dynamicOptionOverrides);
            warnUnknownOptions(extra);
            this.nowManager.handleInput(optionsData.dateEnv, refinedOptions.now);
            let dateProfileGenerator = this.buildDateProfileGenerator({
                dateProfileGeneratorClass: viewSpec.optionDefaults.dateProfileGeneratorClass,
                nowManager: this.nowManager,
                duration: viewSpec.duration,
                durationUnit: viewSpec.durationUnit,
                usesMinMaxTime: viewSpec.optionDefaults.usesMinMaxTime,
                dateEnv: optionsData.dateEnv,
                calendarApi: this.props.calendarApi,
                slotMinTime: refinedOptions.slotMinTime,
                slotMaxTime: refinedOptions.slotMaxTime,
                showNonCurrentDates: refinedOptions.showNonCurrentDates,
                dayCount: refinedOptions.dayCount,
                dateAlignment: refinedOptions.dateAlignment,
                dateIncrement: refinedOptions.dateIncrement,
                hiddenDays: refinedOptions.hiddenDays,
                weekends: refinedOptions.weekends,
                validRangeInput: refinedOptions.validRange,
                visibleRangeInput: refinedOptions.visibleRange,
                fixedWeekCount: refinedOptions.fixedWeekCount,
            });
            let viewApi = this.buildViewApi(viewType, this.getCurrentData, optionsData.dateEnv);
            return { viewSpec, options: refinedOptions, dateProfileGenerator, viewApi };
        }
        processRawViewOptions(viewSpec, pluginHooks, localeDefaults, optionOverrides, dynamicOptionOverrides) {
            let raw = mergeRawOptions([
                BASE_OPTION_DEFAULTS,
                viewSpec.optionDefaults,
                localeDefaults,
                optionOverrides,
                viewSpec.optionOverrides,
                dynamicOptionOverrides,
            ]);
            let refiners = Object.assign(Object.assign(Object.assign(Object.assign(Object.assign(Object.assign({}, BASE_OPTION_REFINERS), CALENDAR_LISTENER_REFINERS), CALENDAR_OPTION_REFINERS), VIEW_OPTION_REFINERS), pluginHooks.listenerRefiners), pluginHooks.optionRefiners);
            let refined = {};
            let currentRaw = this.currentViewOptionsInput;
            let currentRefined = this.currentViewOptionsRefined;
            let anyChanges = false;
            let extra = {};
            for (let optionName in raw) {
                if (raw[optionName] === currentRaw[optionName] ||
                    (COMPLEX_OPTION_COMPARATORS[optionName] &&
                        COMPLEX_OPTION_COMPARATORS[optionName](raw[optionName], currentRaw[optionName]))) {
                    refined[optionName] = currentRefined[optionName];
                }
                else {
                    if (raw[optionName] === this.currentCalendarOptionsInput[optionName] ||
                        (COMPLEX_OPTION_COMPARATORS[optionName] &&
                            COMPLEX_OPTION_COMPARATORS[optionName](raw[optionName], this.currentCalendarOptionsInput[optionName]))) {
                        if (optionName in this.currentCalendarOptionsRefined) { // might be an "extra" prop
                            refined[optionName] = this.currentCalendarOptionsRefined[optionName];
                        }
                    }
                    else if (refiners[optionName]) {
                        refined[optionName] = refiners[optionName](raw[optionName]);
                    }
                    else {
                        extra[optionName] = raw[optionName];
                    }
                    anyChanges = true;
                }
            }
            if (anyChanges) {
                this.currentViewOptionsInput = raw;
                this.currentViewOptionsRefined = refined;
            }
            return {
                rawOptions: this.currentViewOptionsInput,
                refinedOptions: this.currentViewOptionsRefined,
                extra,
            };
        }
    }
    function buildDateEnv$1(timeZone, explicitLocale, weekNumberCalculation, firstDay, weekText, pluginHooks, availableLocaleData, defaultSeparator) {
        let locale = buildLocale(explicitLocale || availableLocaleData.defaultCode, availableLocaleData.map);
        return new DateEnv({
            calendarSystem: 'gregory',
            timeZone,
            namedTimeZoneImpl: pluginHooks.namedTimeZonedImpl,
            locale,
            weekNumberCalculation,
            firstDay,
            weekText,
            cmdFormatter: pluginHooks.cmdFormatter,
            defaultSeparator,
        });
    }
    function buildTheme(options, pluginHooks) {
        let ThemeClass = pluginHooks.themeClasses[options.themeSystem] || StandardTheme;
        return new ThemeClass(options);
    }
    function buildDateProfileGenerator(props) {
        let DateProfileGeneratorClass = props.dateProfileGeneratorClass || DateProfileGenerator;
        return new DateProfileGeneratorClass(props);
    }
    function buildViewApi(type, getCurrentData, dateEnv) {
        return new ViewImpl(type, getCurrentData, dateEnv);
    }
    function buildEventUiBySource(eventSources) {
        return mapHash(eventSources, (eventSource) => eventSource.ui);
    }
    function buildEventUiBases(eventDefs, eventUiSingleBase, eventUiBySource) {
        let eventUiBases = { '': eventUiSingleBase };
        for (let defId in eventDefs) {
            let def = eventDefs[defId];
            if (def.sourceId && eventUiBySource[def.sourceId]) {
                eventUiBases[defId] = eventUiBySource[def.sourceId];
            }
        }
        return eventUiBases;
    }
    function buildViewUiProps(calendarContext) {
        let { options } = calendarContext;
        return {
            eventUiSingleBase: createEventUi({
                display: options.eventDisplay,
                editable: options.editable,
                startEditable: options.eventStartEditable,
                durationEditable: options.eventDurationEditable,
                constraint: options.eventConstraint,
                overlap: typeof options.eventOverlap === 'boolean' ? options.eventOverlap : undefined,
                allow: options.eventAllow,
                backgroundColor: options.eventBackgroundColor,
                borderColor: options.eventBorderColor,
                textColor: options.eventTextColor,
                color: options.eventColor,
                // classNames: options.eventClassNames // render hook will handle this
            }, calendarContext),
            selectionConfig: createEventUi({
                constraint: options.selectConstraint,
                overlap: typeof options.selectOverlap === 'boolean' ? options.selectOverlap : undefined,
                allow: options.selectAllow,
            }, calendarContext),
        };
    }
    function computeIsLoading(state, context) {
        for (let isLoadingFunc of context.pluginHooks.isLoadingFuncs) {
            if (isLoadingFunc(state)) {
                return true;
            }
        }
        return false;
    }
    function parseContextBusinessHours(calendarContext) {
        return parseBusinessHours(calendarContext.options.businessHours, calendarContext);
    }
    function warnUnknownOptions(options, viewName) {
        for (let optionName in options) {
            console.warn(`Unknown option '${optionName}'` +
                (viewName ? ` for view '${viewName}'` : ''));
        }
    }

    class ToolbarSection extends BaseComponent {
        render() {
            let children = this.props.widgetGroups.map((widgetGroup) => this.renderWidgetGroup(widgetGroup));
            return y('div', { className: 'fc-toolbar-chunk' }, ...children);
        }
        renderWidgetGroup(widgetGroup) {
            let { props } = this;
            let { theme } = this.context;
            let children = [];
            let isOnlyButtons = true;
            for (let widget of widgetGroup) {
                let { buttonName, buttonClick, buttonText, buttonIcon, buttonHint } = widget;
                if (buttonName === 'title') {
                    isOnlyButtons = false;
                    children.push(y("h2", { className: "fc-toolbar-title", id: props.titleId }, props.title));
                }
                else {
                    let isPressed = buttonName === props.activeButton;
                    let isDisabled = (!props.isTodayEnabled && buttonName === 'today') ||
                        (!props.isPrevEnabled && buttonName === 'prev') ||
                        (!props.isNextEnabled && buttonName === 'next');
                    let buttonClasses = [`fc-${buttonName}-button`, theme.getClass('button')];
                    if (isPressed) {
                        buttonClasses.push(theme.getClass('buttonActive'));
                    }
                    children.push(y("button", { type: "button", title: typeof buttonHint === 'function' ? buttonHint(props.navUnit) : buttonHint, disabled: isDisabled, "aria-pressed": isPressed, className: buttonClasses.join(' '), onClick: buttonClick }, buttonText || (buttonIcon ? y("span", { className: buttonIcon, role: "img" }) : '')));
                }
            }
            if (children.length > 1) {
                let groupClassName = (isOnlyButtons && theme.getClass('buttonGroup')) || '';
                return y('div', { className: groupClassName }, ...children);
            }
            return children[0];
        }
    }

    class Toolbar extends BaseComponent {
        render() {
            let { model, extraClassName } = this.props;
            let forceLtr = false;
            let startContent;
            let endContent;
            let sectionWidgets = model.sectionWidgets;
            let centerContent = sectionWidgets.center;
            if (sectionWidgets.left) {
                forceLtr = true;
                startContent = sectionWidgets.left;
            }
            else {
                startContent = sectionWidgets.start;
            }
            if (sectionWidgets.right) {
                forceLtr = true;
                endContent = sectionWidgets.right;
            }
            else {
                endContent = sectionWidgets.end;
            }
            let classNames = [
                extraClassName || '',
                'fc-toolbar',
                forceLtr ? 'fc-toolbar-ltr' : '',
            ];
            return (y("div", { className: classNames.join(' ') },
                this.renderSection('start', startContent || []),
                this.renderSection('center', centerContent || []),
                this.renderSection('end', endContent || [])));
        }
        renderSection(key, widgetGroups) {
            let { props } = this;
            return (y(ToolbarSection, { key: key, widgetGroups: widgetGroups, title: props.title, navUnit: props.navUnit, activeButton: props.activeButton, isTodayEnabled: props.isTodayEnabled, isPrevEnabled: props.isPrevEnabled, isNextEnabled: props.isNextEnabled, titleId: props.titleId }));
        }
    }

    class ViewHarness extends BaseComponent {
        constructor() {
            super(...arguments);
            this.state = {
                availableWidth: null,
            };
            this.handleEl = (el) => {
                this.el = el;
                setRef(this.props.elRef, el);
                this.updateAvailableWidth();
            };
            this.handleResize = () => {
                this.updateAvailableWidth();
            };
        }
        render() {
            let { props, state } = this;
            let { aspectRatio } = props;
            let classNames = [
                'fc-view-harness',
                (aspectRatio || props.liquid || props.height)
                    ? 'fc-view-harness-active' // harness controls the height
                    : 'fc-view-harness-passive', // let the view do the height
            ];
            let height = '';
            let paddingBottom = '';
            if (aspectRatio) {
                if (state.availableWidth !== null) {
                    height = state.availableWidth / aspectRatio;
                }
                else {
                    // while waiting to know availableWidth, we can't set height to *zero*
                    // because will cause lots of unnecessary scrollbars within scrollgrid.
                    // BETTER: don't start rendering ANYTHING yet until we know container width
                    // NOTE: why not always use paddingBottom? Causes height oscillation (issue 5606)
                    paddingBottom = `${(1 / aspectRatio) * 100}%`;
                }
            }
            else {
                height = props.height || '';
            }
            return (y("div", { "aria-labelledby": props.labeledById, ref: this.handleEl, className: classNames.join(' '), style: { height, paddingBottom } }, props.children));
        }
        componentDidMount() {
            this.context.addResizeHandler(this.handleResize);
        }
        componentWillUnmount() {
            this.context.removeResizeHandler(this.handleResize);
        }
        updateAvailableWidth() {
            if (this.el && // needed. but why?
                this.props.aspectRatio // aspectRatio is the only height setting that needs availableWidth
            ) {
                this.setState({ availableWidth: this.el.offsetWidth });
            }
        }
    }

    /*
    Detects when the user clicks on an event within a DateComponent
    */
    class EventClicking extends Interaction {
        constructor(settings) {
            super(settings);
            this.handleSegClick = (ev, segEl) => {
                let { component } = this;
                let { context } = component;
                let seg = getElSeg(segEl);
                if (seg && // might be the <div> surrounding the more link
                    component.isValidSegDownEl(ev.target)) {
                    // our way to simulate a link click for elements that can't be <a> tags
                    // grab before trigger fired in case trigger trashes DOM thru rerendering
                    let hasUrlContainer = elementClosest(ev.target, '.fc-event-forced-url');
                    let url = hasUrlContainer ? hasUrlContainer.querySelector('a[href]').href : '';
                    context.emitter.trigger('eventClick', {
                        el: segEl,
                        event: new EventImpl(component.context, seg.eventRange.def, seg.eventRange.instance),
                        jsEvent: ev,
                        view: context.viewApi,
                    });
                    if (url && !ev.defaultPrevented) {
                        window.location.href = url;
                    }
                }
            };
            this.destroy = listenBySelector(settings.el, 'click', '.fc-event', // on both fg and bg events
            this.handleSegClick);
        }
    }

    /*
    Triggers events and adds/removes core classNames when the user's pointer
    enters/leaves event-elements of a component.
    */
    class EventHovering extends Interaction {
        constructor(settings) {
            super(settings);
            // for simulating an eventMouseLeave when the event el is destroyed while mouse is over it
            this.handleEventElRemove = (el) => {
                if (el === this.currentSegEl) {
                    this.handleSegLeave(null, this.currentSegEl);
                }
            };
            this.handleSegEnter = (ev, segEl) => {
                if (getElSeg(segEl)) { // TODO: better way to make sure not hovering over more+ link or its wrapper
                    this.currentSegEl = segEl;
                    this.triggerEvent('eventMouseEnter', ev, segEl);
                }
            };
            this.handleSegLeave = (ev, segEl) => {
                if (this.currentSegEl) {
                    this.currentSegEl = null;
                    this.triggerEvent('eventMouseLeave', ev, segEl);
                }
            };
            this.removeHoverListeners = listenToHoverBySelector(settings.el, '.fc-event', // on both fg and bg events
            this.handleSegEnter, this.handleSegLeave);
        }
        destroy() {
            this.removeHoverListeners();
        }
        triggerEvent(publicEvName, ev, segEl) {
            let { component } = this;
            let { context } = component;
            let seg = getElSeg(segEl);
            if (!ev || component.isValidSegDownEl(ev.target)) {
                context.emitter.trigger(publicEvName, {
                    el: segEl,
                    event: new EventImpl(context, seg.eventRange.def, seg.eventRange.instance),
                    jsEvent: ev,
                    view: context.viewApi,
                });
            }
        }
    }

    class CalendarContent extends PureComponent {
        constructor() {
            super(...arguments);
            this.buildViewContext = memoize(buildViewContext);
            this.buildViewPropTransformers = memoize(buildViewPropTransformers);
            this.buildToolbarProps = memoize(buildToolbarProps);
            this.headerRef = d();
            this.footerRef = d();
            this.interactionsStore = {};
            // eslint-disable-next-line
            this.state = {
                viewLabelId: getUniqueDomId(),
            };
            // Component Registration
            // -----------------------------------------------------------------------------------------------------------------
            this.registerInteractiveComponent = (component, settingsInput) => {
                let settings = parseInteractionSettings(component, settingsInput);
                let DEFAULT_INTERACTIONS = [
                    EventClicking,
                    EventHovering,
                ];
                let interactionClasses = DEFAULT_INTERACTIONS.concat(this.props.pluginHooks.componentInteractions);
                let interactions = interactionClasses.map((TheInteractionClass) => new TheInteractionClass(settings));
                this.interactionsStore[component.uid] = interactions;
                interactionSettingsStore[component.uid] = settings;
            };
            this.unregisterInteractiveComponent = (component) => {
                let listeners = this.interactionsStore[component.uid];
                if (listeners) {
                    for (let listener of listeners) {
                        listener.destroy();
                    }
                    delete this.interactionsStore[component.uid];
                }
                delete interactionSettingsStore[component.uid];
            };
            // Resizing
            // -----------------------------------------------------------------------------------------------------------------
            this.resizeRunner = new DelayedRunner(() => {
                this.props.emitter.trigger('_resize', true); // should window resizes be considered "forced" ?
                this.props.emitter.trigger('windowResize', { view: this.props.viewApi });
            });
            this.handleWindowResize = (ev) => {
                let { options } = this.props;
                if (options.handleWindowResize &&
                    ev.target === window // avoid jqui events
                ) {
                    this.resizeRunner.request(options.windowResizeDelay);
                }
            };
        }
        /*
        renders INSIDE of an outer div
        */
        render() {
            let { props } = this;
            let { toolbarConfig, options } = props;
            let viewVGrow = false;
            let viewHeight = '';
            let viewAspectRatio;
            if (props.isHeightAuto || props.forPrint) {
                viewHeight = '';
            }
            else if (options.height != null) {
                viewVGrow = true;
            }
            else if (options.contentHeight != null) {
                viewHeight = options.contentHeight;
            }
            else {
                viewAspectRatio = Math.max(options.aspectRatio, 0.5); // prevent from getting too tall
            }
            let viewContext = this.buildViewContext(props.viewSpec, props.viewApi, props.options, props.dateProfileGenerator, props.dateEnv, props.nowManager, props.theme, props.pluginHooks, props.dispatch, props.getCurrentData, props.emitter, props.calendarApi, this.registerInteractiveComponent, this.unregisterInteractiveComponent);
            let viewLabelId = (toolbarConfig.header && toolbarConfig.header.hasTitle)
                ? this.state.viewLabelId
                : undefined;
            return (y(ViewContextType.Provider, { value: viewContext },
                y(NowTimer, { unit: "day" }, (nowDate) => {
                    let toolbarProps = this.buildToolbarProps(props.viewSpec, props.dateProfile, props.dateProfileGenerator, props.currentDate, nowDate, props.viewTitle);
                    return (y(_, null,
                        toolbarConfig.header && (y(Toolbar, Object.assign({ ref: this.headerRef, extraClassName: "fc-header-toolbar", model: toolbarConfig.header, titleId: viewLabelId }, toolbarProps))),
                        y(ViewHarness, { liquid: viewVGrow, height: viewHeight, aspectRatio: viewAspectRatio, labeledById: viewLabelId },
                            this.renderView(props),
                            this.buildAppendContent()),
                        toolbarConfig.footer && (y(Toolbar, Object.assign({ ref: this.footerRef, extraClassName: "fc-footer-toolbar", model: toolbarConfig.footer, titleId: "" }, toolbarProps)))));
                })));
        }
        componentDidMount() {
            let { props } = this;
            this.calendarInteractions = props.pluginHooks.calendarInteractions
                .map((CalendarInteractionClass) => new CalendarInteractionClass(props));
            window.addEventListener('resize', this.handleWindowResize);
            let { propSetHandlers } = props.pluginHooks;
            for (let propName in propSetHandlers) {
                propSetHandlers[propName](props[propName], props);
            }
        }
        componentDidUpdate(prevProps) {
            let { props } = this;
            let { propSetHandlers } = props.pluginHooks;
            for (let propName in propSetHandlers) {
                if (props[propName] !== prevProps[propName]) {
                    propSetHandlers[propName](props[propName], props);
                }
            }
        }
        componentWillUnmount() {
            window.removeEventListener('resize', this.handleWindowResize);
            this.resizeRunner.clear();
            for (let interaction of this.calendarInteractions) {
                interaction.destroy();
            }
            this.props.emitter.trigger('_unmount');
        }
        buildAppendContent() {
            let { props } = this;
            let children = props.pluginHooks.viewContainerAppends.map((buildAppendContent) => buildAppendContent(props));
            return y(_, {}, ...children);
        }
        renderView(props) {
            let { pluginHooks } = props;
            let { viewSpec } = props;
            let viewProps = {
                dateProfile: props.dateProfile,
                businessHours: props.businessHours,
                eventStore: props.renderableEventStore,
                eventUiBases: props.eventUiBases,
                dateSelection: props.dateSelection,
                eventSelection: props.eventSelection,
                eventDrag: props.eventDrag,
                eventResize: props.eventResize,
                isHeightAuto: props.isHeightAuto,
                forPrint: props.forPrint,
            };
            let transformers = this.buildViewPropTransformers(pluginHooks.viewPropsTransformers);
            for (let transformer of transformers) {
                Object.assign(viewProps, transformer.transform(viewProps, props));
            }
            let ViewComponent = viewSpec.component;
            return (y(ViewComponent, Object.assign({}, viewProps)));
        }
    }
    function buildToolbarProps(viewSpec, dateProfile, dateProfileGenerator, currentDate, now, title) {
        // don't force any date-profiles to valid date profiles (the `false`) so that we can tell if it's invalid
        let todayInfo = dateProfileGenerator.build(now, undefined, false); // TODO: need `undefined` or else INFINITE LOOP for some reason
        let prevInfo = dateProfileGenerator.buildPrev(dateProfile, currentDate, false);
        let nextInfo = dateProfileGenerator.buildNext(dateProfile, currentDate, false);
        return {
            title,
            activeButton: viewSpec.type,
            navUnit: viewSpec.singleUnit,
            isTodayEnabled: todayInfo.isValid && !rangeContainsMarker(dateProfile.currentRange, now),
            isPrevEnabled: prevInfo.isValid,
            isNextEnabled: nextInfo.isValid,
        };
    }
    // Plugin
    // -----------------------------------------------------------------------------------------------------------------
    function buildViewPropTransformers(theClasses) {
        return theClasses.map((TheClass) => new TheClass());
    }

    class Calendar extends CalendarImpl {
        constructor(el, optionOverrides = {}) {
            super();
            this.isRendering = false;
            this.isRendered = false;
            this.currentClassNames = [];
            this.customContentRenderId = 0;
            this.handleAction = (action) => {
                // actions we know we want to render immediately
                switch (action.type) {
                    case 'SET_EVENT_DRAG':
                    case 'SET_EVENT_RESIZE':
                        this.renderRunner.tryDrain();
                }
            };
            this.handleData = (data) => {
                this.currentData = data;
                this.renderRunner.request(data.calendarOptions.rerenderDelay);
            };
            this.handleRenderRequest = () => {
                if (this.isRendering) {
                    this.isRendered = true;
                    let { currentData } = this;
                    flushSync(() => {
                        D$1(y(CalendarRoot, { options: currentData.calendarOptions, theme: currentData.theme, emitter: currentData.emitter }, (classNames, height, isHeightAuto, forPrint) => {
                            this.setClassNames(classNames);
                            this.setHeight(height);
                            return (y(RenderId.Provider, { value: this.customContentRenderId },
                                y(CalendarContent, Object.assign({ isHeightAuto: isHeightAuto, forPrint: forPrint }, currentData))));
                        }), this.el);
                    });
                }
                else if (this.isRendered) {
                    this.isRendered = false;
                    D$1(null, this.el);
                    this.setClassNames([]);
                    this.setHeight('');
                }
            };
            ensureElHasStyles(el);
            this.el = el;
            this.renderRunner = new DelayedRunner(this.handleRenderRequest);
            new CalendarDataManager({
                optionOverrides,
                calendarApi: this,
                onAction: this.handleAction,
                onData: this.handleData,
            });
        }
        render() {
            let wasRendering = this.isRendering;
            if (!wasRendering) {
                this.isRendering = true;
            }
            else {
                this.customContentRenderId += 1;
            }
            this.renderRunner.request();
            if (wasRendering) {
                this.updateSize();
            }
        }
        destroy() {
            if (this.isRendering) {
                this.isRendering = false;
                this.renderRunner.request();
            }
        }
        updateSize() {
            flushSync(() => {
                super.updateSize();
            });
        }
        batchRendering(func) {
            this.renderRunner.pause('batchRendering');
            func();
            this.renderRunner.resume('batchRendering');
        }
        pauseRendering() {
            this.renderRunner.pause('pauseRendering');
        }
        resumeRendering() {
            this.renderRunner.resume('pauseRendering', true);
        }
        resetOptions(optionOverrides, changedOptionNames) {
            this.currentDataManager.resetOptions(optionOverrides, changedOptionNames);
        }
        setClassNames(classNames) {
            if (!isArraysEqual(classNames, this.currentClassNames)) {
                let { classList } = this.el;
                for (let className of this.currentClassNames) {
                    classList.remove(className);
                }
                for (let className of classNames) {
                    classList.add(className);
                }
                this.currentClassNames = classNames;
            }
        }
        setHeight(height) {
            applyStyleProp(this.el, 'height', height);
        }
    }

    function formatDate(dateInput, options = {}) {
        let dateEnv = buildDateEnv(options);
        let formatter = createFormatter(options);
        let dateMeta = dateEnv.createMarkerMeta(dateInput);
        if (!dateMeta) { // TODO: warning?
            return '';
        }
        return dateEnv.format(dateMeta.marker, formatter, {
            forcedTzo: dateMeta.forcedTzo,
        });
    }
    function formatRange(startInput, endInput, options) {
        let dateEnv = buildDateEnv(typeof options === 'object' && options ? options : {}); // pass in if non-null object
        let formatter = createFormatter(options);
        let startMeta = dateEnv.createMarkerMeta(startInput);
        let endMeta = dateEnv.createMarkerMeta(endInput);
        if (!startMeta || !endMeta) { // TODO: warning?
            return '';
        }
        return dateEnv.formatRange(startMeta.marker, endMeta.marker, formatter, {
            forcedStartTzo: startMeta.forcedTzo,
            forcedEndTzo: endMeta.forcedTzo,
            isEndExclusive: options.isEndExclusive,
            defaultSeparator: BASE_OPTION_DEFAULTS.defaultRangeSeparator,
        });
    }
    // TODO: more DRY and optimized
    function buildDateEnv(settings) {
        let locale = buildLocale(settings.locale || 'en', organizeRawLocales([]).map); // TODO: don't hardcode 'en' everywhere
        return new DateEnv(Object.assign(Object.assign({ timeZone: BASE_OPTION_DEFAULTS.timeZone, calendarSystem: 'gregory' }, settings), { locale }));
    }

    // HELPERS
    /*
    if nextDayThreshold is specified, slicing is done in an all-day fashion.
    you can get nextDayThreshold from context.nextDayThreshold
    */
    function sliceEvents(props, allDay) {
        return sliceEventStore(props.eventStore, props.eventUiBases, props.dateProfile.activeRange, allDay ? props.nextDayThreshold : null).fg;
    }

    const version = '6.1.20';

    exports.Calendar = Calendar;
    exports.Internal = internal;
    exports.JsonRequestError = JsonRequestError;
    exports.Preact = preact;
    exports.createPlugin = createPlugin;
    exports.formatDate = formatDate;
    exports.formatRange = formatRange;
    exports.globalLocales = globalLocales;
    exports.globalPlugins = globalPlugins;
    exports.sliceEvents = sliceEvents;
    exports.version = version;

    Object.defineProperty(exports, '__esModule', { value: true });

    return exports;

})({});
