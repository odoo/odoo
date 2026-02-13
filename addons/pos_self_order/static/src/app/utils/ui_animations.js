const ANIMATION_CONFIG = {
    flyDuration: "900ms",
    cartDuration: "200ms",
    flyEasing: "cubic-bezier(0.34, 1.56, 0.64, 1)",
    initialScale: ".65",
    finalScale: "0.05",
    cartScale: "1.08",
    rotation: "5deg",
};

export function flyToCart(eventTarget, destinationSelector = ".to-order") {
    if (!eventTarget) {
        return;
    }
    const productEl = eventTarget.closest(".o_self_product_box");

    const destinationEl = document.querySelector(destinationSelector);
    if (!destinationEl || window.getComputedStyle(destinationEl).display === "none" || !productEl) {
        return;
    }

    const cardRect = productEl.getBoundingClientRect();
    const destinationRect = destinationEl.getBoundingClientRect();
    const offsetTop = destinationRect.top - cardRect.top;
    const offsetLeft = destinationRect.left - cardRect.left;

    const clonedPic = productEl.cloneNode(true);
    const initialStyles = {
        top: `${cardRect.top}px`,
        left: `${cardRect.left}px`,
        width: `${cardRect.width}px`,
        height: `${cardRect.height}px`,
        transform: "scale(1)",
        opacity: "1",
        transition: `all ${ANIMATION_CONFIG.flyDuration} ${ANIMATION_CONFIG.flyEasing}`,
        pointerEvents: "none",
    };

    const wrapper = document.createElement("div");
    Object.assign(wrapper.style, initialStyles);
    wrapper.classList.add("position-fixed", "o_self_product_list_page", "shadow-lg", "z-1");
    wrapper.appendChild(clonedPic);

    const infosDiv = clonedPic.querySelector(".product-infos");
    if (infosDiv) {
        Object.assign(infosDiv.style, {
            transform: "scale(0.9)",
            transition: `all ${ANIMATION_CONFIG.flyDuration} ${ANIMATION_CONFIG.flyEasing}`,
        });
    }

    document.body.appendChild(wrapper);

    requestAnimationFrame(() => {
        wrapper.style.transform = `scale(${ANIMATION_CONFIG.initialScale})`;
        requestAnimationFrame(() => {
            wrapper.style.transform = `
                    translateY(${offsetTop}px)
                    translateX(${offsetLeft}px)
                    scale(${ANIMATION_CONFIG.finalScale})
                    rotate(${ANIMATION_CONFIG.rotation})
                `;
            wrapper.style.opacity = "0";

            if (infosDiv) {
                infosDiv.style.transform = "scale(0.7)";
            }

            const cartAnimation = {
                transform: `scale(${ANIMATION_CONFIG.cartScale})`,
                transition: `transform ${ANIMATION_CONFIG.cartDuration} ${ANIMATION_CONFIG.flyEasing}`,
            };
            Object.assign(destinationEl.style, cartAnimation);

            setTimeout(() => {
                Object.assign(destinationEl.style, {
                    transform: "scale(1)",
                    transition: `transform ${ANIMATION_CONFIG.cartDuration} ${ANIMATION_CONFIG.flyEasing}`,
                });
            }, parseInt(ANIMATION_CONFIG.cartDuration));
        });
    });

    wrapper.addEventListener("transitionend", () => {
        wrapper.remove();
    });
}
