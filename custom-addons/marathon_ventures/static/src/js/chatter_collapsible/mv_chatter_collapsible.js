/** @odoo-module **/
/* ============================================================================
   MV - Chatter Width Toggle
   ----------------------------------------------------------------------------
   Injects a small round toggle button into every Odoo chatter's header
   bar (.o-mail-Chatter-top). Clicking it flips the chatter between two
   states:

     - "narrow"   : 100px sliver on the right (default on first load)
     - "expanded" : full original width

   The chatter content stays mounted; we just change the panel width and
   let overflow:hidden clip the rest. The user's preference is persisted
   in localStorage.
   ============================================================================ */

const TOGGLE_CLASS = "mv-chatter-toggle";
const NARROW_CLASS = "mv-chatter--narrow";
const STORAGE_KEY  = "mv.chatterNarrow";

function preferenceNarrow() {
    try {
        const v = window.localStorage.getItem(STORAGE_KEY);
        return v !== "0";   // default narrow; only "0" means expanded
    } catch (e) {
        return true;
    }
}

function savePreference(narrow) {
    try {
        window.localStorage.setItem(STORAGE_KEY, narrow ? "1" : "0");
    } catch (e) {
        /* localStorage blocked - ignore */
    }
}

function injectToggle(chatter) {
    if (!chatter) return;
    // Idempotency: look for the button ANYWHERE in the chatter subtree.
    if (chatter.querySelector("." + TOGGLE_CLASS)) return;

    // Apply persisted width preference immediately. This way the panel
    // is already narrow on the first paint even if the header element
    // (.o-mail-Chatter-top) mounts a tick later.
    if (preferenceNarrow()) {
        chatter.classList.add(NARROW_CLASS);
    }

    const top = chatter.querySelector(".o-mail-Chatter-top");
    if (!top) {
        // Header hasn't mounted yet. The MutationObserver in boot() will
        // call us again once it appears.
        return;
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = TOGGLE_CLASS;
    button.setAttribute("title", "Toggle chatter width (collapse / expand)");
    button.setAttribute("aria-label", "Toggle chatter");

    const onClick = (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        const willNarrow = !chatter.classList.contains(NARROW_CLASS);
        chatter.classList.toggle(NARROW_CLASS, willNarrow);
        savePreference(willNarrow);
    };

    button.addEventListener("click", onClick);
    button.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
            onClick(ev);
        }
    });

    top.prepend(button);
}

function scan(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll(".o-mail-ChatterContainer").forEach(injectToggle);
}

function boot() {
    scan(document);
    const obs = new MutationObserver((mutations) => {
        let needRescan = false;
        for (const m of mutations) {
            for (const node of m.addedNodes) {
                if (!(node instanceof Element)) continue;
                if (
                    (node.classList && (
                        node.classList.contains("o-mail-ChatterContainer") ||
                        node.classList.contains("o-mail-Chatter-top")
                    )) ||
                    (node.querySelector && node.querySelector(".o-mail-ChatterContainer, .o-mail-Chatter-top"))
                ) {
                    needRescan = true;
                    break;
                }
            }
            if (needRescan) break;
        }
        if (needRescan) scan(document);
    });
    obs.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
    boot();
}
