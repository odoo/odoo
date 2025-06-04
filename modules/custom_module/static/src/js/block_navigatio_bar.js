/** @odoo-module */

function detecterConnexion() {
    if (!navigator.onLine) {
        console.warn('🔴 Hors ligne : désactivation du refresh et retour navigateur.');
        disableRefresh();
        disableBackButton();
    } else {
        console.info('🟢 En ligne : réactivation du refresh et retour navigateur.');
        enableRefresh();
        enableBackButton();
    }
}

// =====================
// Gestion du Refresh
// =====================

function preventRefresh(event) {
    const isCtrlR = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'r';
    const isF5 = event.key === 'F5' || event.keyCode === 116;

    if (isCtrlR || isF5) {
        event.preventDefault();
        console.warn("⛔ Rafraîchissement désactivé !");
    }
}


function disableRefresh() {
    document.addEventListener('keydown', preventRefresh);
    window.onbeforeunload = () => "Vous êtes hors ligne. Êtes-vous sûr de vouloir quitter cette page ?";
}

function enableRefresh() {
    document.removeEventListener('keydown', preventRefresh);
    window.onbeforeunload = null;
}

// =====================
// Gestion du bouton "Retour"
// =====================

let backBlocker = null;

function disableBackButton() {
    history.pushState(null, null, location.href);
    backBlocker = function () {
        history.pushState(null, null, location.href);
    };
    window.addEventListener('popstate', backBlocker);
}

function enableBackButton() {
    if (backBlocker) {
        window.removeEventListener('popstate', backBlocker);
        backBlocker = null;
    }
}

// =====================
// Initialisation
// =====================

detecterConnexion();

// Écoute les changements de statut réseau
window.addEventListener('online', detecterConnexion);
window.addEventListener('offline', detecterConnexion);
