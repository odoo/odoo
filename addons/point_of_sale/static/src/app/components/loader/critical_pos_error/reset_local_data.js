const ignoreErrors = async (callback) => {
    try {
        await callback();
    } catch {
        // Ignore cleanup failures.
    }
};

const deleteDatabase = (name) =>
    Promise.race([
        new Promise((resolve) => {
            const request = indexedDB.deleteDatabase(name);
            request.onsuccess = resolve;
            request.onerror = resolve;
            request.onblocked = resolve;
        }),
        new Promise((resolve) => setTimeout(resolve, 1500)),
    ]);

export async function resetLocalData() {
    const tasks = [
        ignoreErrors(() => localStorage.clear()),
        ignoreErrors(() => sessionStorage.clear()),
    ];

    if ("serviceWorker" in navigator) {
        tasks.push(
            ignoreErrors(async () => {
                const registrations = await navigator.serviceWorker.getRegistrations();
                await Promise.allSettled(
                    registrations.map((registration) => registration.unregister())
                );
            })
        );
    }

    if ("caches" in window) {
        tasks.push(
            ignoreErrors(async () => {
                const cacheNames = await caches.keys();
                await Promise.allSettled(cacheNames.map((name) => caches.delete(name)));
            })
        );
    }

    if ("indexedDB" in window && typeof indexedDB.databases === "function") {
        tasks.push(
            ignoreErrors(async () => {
                const databases = await indexedDB.databases();
                const names = databases.flatMap((db) => (db?.name ? [db.name] : []));
                await Promise.allSettled(names.map(deleteDatabase));
            })
        );
    }

    await Promise.all(tasks);
    location.reload();
}
