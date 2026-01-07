import { Component, useState } from "@odoo/owl";

export class CriticalPOSError extends Component {
    static template = "point_of_sale.CriticalPOSError";
    static props = { error: Object };

    setup() {
        this.state = useState({ expanded: false });
    }
    async fullReset() {
        const step = async (fn) => {
            try {
                await fn();
            } catch {
                // keep going
            }
        };

        try {
            // Storage
            await step(() => localStorage.clear());
            await step(() => sessionStorage.clear());

            // Unregister service workers

            if ("serviceWorker" in navigator) {
                await step(async () => {
                    const regs = await navigator.serviceWorker.getRegistrations();
                    await Promise.allSettled(regs.map((r) => r.unregister()));
                });
            }

            // Clear Cache Storage (important for PWAs)
            if ("caches" in window) {
                await step(async () => {
                    const keys = await caches.keys();
                    await Promise.allSettled(keys.map((k) => caches.delete(k)));
                });
            }

            // Delete IndexedDB databases (if supported)
            if ("indexedDB" in window && typeof indexedDB.databases === "function") {
                await step(async () => {
                    const dbs = await indexedDB.databases();
                    const names = dbs.map((db) => db?.name).filter(Boolean);
                    await Promise.allSettled(
                        names.map((name) =>
                            Promise.race([
                                new Promise((resolve, reject) => {
                                    const req = indexedDB.deleteDatabase(name);
                                    req.onsuccess = () => resolve();
                                    req.onerror = () => resolve();
                                    req.onblocked = () => resolve();
                                }),
                                new Promise((resolve) =>
                                    setTimeout(() => {
                                        resolve();
                                    }, 1500)
                                ),
                            ])
                        )
                    );
                });
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
