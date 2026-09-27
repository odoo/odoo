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

function normalizeToArray(els) {
    if (els) {
        if (els.nodeName && ["FORM", "SELECT"].includes(els.nodeName)) {
            return [els];
        }
        return els[Symbol.iterator] ? els : [els];
    } else {
        return [];
    }
}

export async function fadeOut(els, duration, afterFadeOutCallback) {
    els = normalizeToArray(els);
    const promises = [];
    for (const el of els) {
        promises.push(animate(el, [{ opacity: 0 }], duration));
    }
    await Promise.all(promises);
    for (const el of els) {
        el.classList.add("d-none");
    }
    afterFadeOutCallback?.();
}

export async function fadeIn(els, duration, afterFadeInCallback) {
    els = normalizeToArray(els);
    const promises = [];
    for (const el of els) {
        el.classList.remove("d-none");
        promises.push(animate(el, [{ opacity: 1 }], duration));
    }
    await Promise.all(promises);
    afterFadeInCallback?.();
}
