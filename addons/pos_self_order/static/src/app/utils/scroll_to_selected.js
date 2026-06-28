export const scrollToSelected = (containerRef, callback, padding = 8) => {
    const scrollToSelected = (itemEl) => {
        // Transitional: Owl 3 native refs are signals (call to read the element);
        // legacy refs expose `.el`. Resolve the element once, supporting both.
        const containerEl = typeof containerRef === "function" ? containerRef() : containerRef?.el;
        const itemRect = itemEl.getBoundingClientRect();
        const containerRect = containerEl.getBoundingClientRect();
        const leftOverflow = itemRect.left - containerRect.left;
        const rightOverflow = itemRect.right - containerRect.right;

        if (leftOverflow < 0) {
            containerEl.scrollBy({
                left: leftOverflow - padding,
                behavior: "smooth",
            });
        } else if (rightOverflow > 0) {
            containerEl.scrollBy({
                left: rightOverflow + padding,
                behavior: "smooth",
            });
        }
    };

    return (event, catId) => {
        callback(catId);
        scrollToSelected(event.currentTarget);
    };
};
