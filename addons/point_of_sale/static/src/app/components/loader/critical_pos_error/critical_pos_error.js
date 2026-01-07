import { Component, useState } from "@odoo/owl";

export class CriticalPOSError extends Component {
    static template = "point_of_sale.CriticalPOSError";
    static props = { error: Object };

    setup() {
        this.state = useState({ expanded: false });
    }
    async fullReset() {
        // Storage
        localStorage.clear();
        sessionStorage.clear();

        try {
            // Unregister service workers
            if ("serviceWorker" in navigator) {
                const regs = await navigator.serviceWorker.getRegistrations();
                await Promise.all(regs.map((r) => r.unregister()));
            }

            // Clear Cache Storage (important for PWAs)
            if ("caches" in window) {
                const keys = await caches.keys();
                await Promise.all(keys.map((k) => caches.delete(k)));
            }

            // Delete IndexedDB databases (if supported)
            if ("indexedDB" in window && typeof indexedDB.databases === "function") {
                const dbs = await indexedDB.databases();
                const names = dbs.map((db) => db?.name).filter(Boolean);
                await Promise.all(
                    names.map(
                        (name) =>
                            new Promise((resolve, reject) => {
                                const req = indexedDB.deleteDatabase(name);
                                req.onsuccess = () => resolve();
                                req.onerror = () => reject(req.error);
                                req.onblocked = () => resolve();
                            })
                    )
                );
            }
        } finally {
            // Reload
            location.reload();
        }
    }
    async copyToClipboard() {
        const text = this.state.expanded ? this.props.error.stack : this.props.error;
        if (!text) {
            return;
        }

        try {
            await navigator.clipboard.writeText(text);
        } catch (err) {
            console.error("Could not copy text: ", err);
        }
    }
    back() {
        window.history.back();
    }
}
