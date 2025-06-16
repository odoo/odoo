async function animate(el, keyFrame, duration) {
    if (!el) {
        return;
    }
    const animation = el.animate(keyFrame, {
        duration,
        iterations: 1,
        fill: "forwards",
    });
    await animation.finished;
    try {
        // can fail when the element is not visible (ex: display: none)
        animation.commitStyles();
    } catch {
        // pass
    }
    animation.cancel();
}

export async function fadeOut(els, duration) {
    const promises = [];
    for (const el of els) {
        promises.push(animate(el, [{ opacity: 0 }], duration));
    }
    await Promise.all(promises);
    for (const el of els) {
        el.classList.add("d-none");
    }
}

export async function fadeIn(els, duration) {
    const promises = [];
    for (const el of els) {
        el.classList.remove("d-none");
        promises.push(animate(el, [{ opacity: 1 }], duration));
    }
    await Promise.all(promises);
}
