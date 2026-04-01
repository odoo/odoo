/** @odoo-module **/

function normalizeText(value) {
    return (value || "").trim().toLowerCase();
}

function parseCandidateInfo(card) {
    const dataValues = [
        card.dataset.moduleName,
        card.dataset.menuXmlid,
        card.dataset.xmlid,
        card.getAttribute("data-module"),
        card.getAttribute("data-module-name"),
    ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

    const hrefValues = Array.from(card.querySelectorAll("a[href]"))
        .map((link) => link.getAttribute("href") || "")
        .join(" ")
        .toLowerCase();

    const nameEl = card.querySelector(
        ".o_app_name, .o_module_name, .card-title, strong, h4, h5, h6"
    );
    const name = normalizeText(nameEl ? nameEl.textContent : "");
    const fullText = normalizeText(card.textContent);

    return {
        dataValues,
        hrefValues,
        name,
        fullText,
        hasUpgrade: fullText.includes("upgrade"),
    };
}

function shouldHideStudioCard(card) {
    const info = parseCandidateInfo(card);
    if (
        info.dataValues.includes("web_studio") ||
        info.hrefValues.includes("web_studio") ||
        info.fullText.includes("web_studio")
    ) {
        return true;
    }
    return info.name === "studio" && info.hasUpgrade;
}

function hideWebStudioCards() {
    if (!window.location.pathname.startsWith("/odoo/apps")) {
        return;
    }
    const selectors = [
        ".o_kanban_record",
        ".o_app",
        ".o_app_module",
        "[data-module-name]",
        "[data-module]",
    ];
    const cards = new Set();
    for (const selector of selectors) {
        document.querySelectorAll(selector).forEach((card) => cards.add(card));
    }
    cards.forEach((card) => {
        if (shouldHideStudioCard(card)) {
            card.style.display = "none";
            card.setAttribute("data-kodoo-web-studio-hidden", "1");
        }
    });
}

const observer = new MutationObserver(() => {
    hideWebStudioCards();
});

function startObserver() {
    hideWebStudioCards();
    if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startObserver, { once: true });
} else {
    startObserver();
}
