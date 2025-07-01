/** @odoo-module **/


function waitForSplashLoader() {
    const splash = document.getElementById("splash-loader");
    if (!splash) {
        // Try again in 100ms
        setTimeout(waitForSplashLoader, 100);
        return;
    }
    setTimeout(() => {
        splash.style.opacity = "0";
        splash.style.transition = "opacity 0.5s ease";
        setTimeout(() => {
            console.log("🗑️ Removiendo splash-loader del DOM");
            splash.remove();
        }, 500);
    }, 700);
}

waitForSplashLoader();
