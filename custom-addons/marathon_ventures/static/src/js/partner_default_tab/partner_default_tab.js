/** @odoo-module **/
/*  Force the "Details" notebook page to be the active tab on every
 *  res.partner form.
 *
 *  Two layers:
 *    1. Primary: patch OWL Notebook.setup so it prefers a page named
 *       `mv_details` when one exists in its pages list. Odoo runs
 *       this on every notebook mount - safe globally because that
 *       name is only used by our res.partner Details page.
 *    2. Fallback: a DOM-level MutationObserver clicks the
 *       .nav-link[name="mv_details"] tab if the OWL patch didn't
 *       take effect on a given render.
 *
 *  Both layers only start work once the DOM is ready. Backend asset
 *  bundles can execute BEFORE <body> exists, so calling
 *  MutationObserver.observe(document.body, ...) at top level throws
 *  "parameter 1 is not of type 'Node'".
 */
import { Notebook } from "@web/core/notebook/notebook";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

const DETAILS_TAB_NAME = "mv_details";


// ---------------------------------------------------------------
// Primary path: patch OWL Notebook.setup (safe at module load)
// ---------------------------------------------------------------
patch(Notebook.prototype, {
    setup() {
        super.setup();
        onMounted(() => {
            try {
                const pages = Array.isArray(this.pages)
                    ? this.pages
                    : (this.state && Array.isArray(this.state.pages)
                        ? this.state.pages : []);
                const details = pages.find(
                    (p) => p && p.name === DETAILS_TAB_NAME,
                );
                if (!details) return;
                if (this.state && "currentPage" in this.state) {
                    this.state.currentPage = details.id;
                } else if (this.state && "activePage" in this.state) {
                    this.state.activePage = details.id;
                }
            } catch (_e) { /* fall through to DOM fallback */ }
        });
    },
});


// ---------------------------------------------------------------
// Fallback path: DOM-level click on the Details tab.
// Everything here must wait for the DOM to exist.
// ---------------------------------------------------------------
function _findDetailsTab(root) {
    if (!root || root.nodeType !== 1 || !root.querySelector) return null;
    return (
        root.querySelector(
            `.o_notebook_headers a.nav-link[name="${DETAILS_TAB_NAME}"]`,
        )
        || root.querySelector(
            `.o_notebook_headers a.nav-link[data-name="${DETAILS_TAB_NAME}"]`,
        )
    );
}

function _activateDetailsTab(root) {
    const tab = _findDetailsTab(root);
    if (!tab) return;
    if (tab.classList.contains("active")) return;
    const notebook = tab.closest(".o_notebook");
    if (notebook && notebook.dataset.mvDetailsActivated) return;
    if (notebook) notebook.dataset.mvDetailsActivated = "1";
    requestAnimationFrame(() => {
        try { tab.click(); } catch (_e) { /* ignore */ }
    });
}

function _scanAll(root) {
    if (!root || !root.querySelectorAll) return;
    const notebooks = root.querySelectorAll(".o_notebook");
    for (const nb of notebooks) {
        _activateDetailsTab(nb);
    }
}

function _startFallback() {
    // At this point document.body is guaranteed to exist.
    _scanAll(document);
    const observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
            if (m.addedNodes && m.addedNodes.length) {
                for (const n of m.addedNodes) {
                    if (n.nodeType === 1) {
                        _scanAll(n);
                        _scanAll(n.parentElement || document);
                        return;
                    }
                }
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _startFallback);
} else {
    // DOM is already parsed (typical for Odoo backend bundles that
    // load after the initial page). Run immediately.
    _startFallback();
}
