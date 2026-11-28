/** Track an impression once per element, including across interaction restarts. */
const viewedElements = new WeakSet();

export function observeTrackingVisibility(interaction, callback) {
    if (viewedElements.has(interaction.el)) return;
    const observer = new IntersectionObserver((entries) => {
        if (viewedElements.has(interaction.el)) return;
        if (!entries.some(entry => entry.isIntersecting && entry.intersectionRatio > 0)) return;
        viewedElements.add(interaction.el);
        observer.disconnect();
        callback();
    });
    interaction.registerCleanup(() => observer.disconnect());
    observer.observe(interaction.el);
}
