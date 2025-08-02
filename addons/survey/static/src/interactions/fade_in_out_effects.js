export function fadeInEffect(target, duration, callback) {
    let opacity = 0;
    target.style.opacity = opacity;
    if (target.style.display === "none") {
        target.style.display = "block";
    }
    const startTime = performance.now();
    function fadeInStep(currentTime) {
        opacity = Math.min((currentTime - startTime) / duration, 1);
        target.style.opacity = opacity;
        if (opacity < 1) {
            requestAnimationFrame(fadeInStep);
        } else if (callback) {
            callback();
        }
    }
    requestAnimationFrame(fadeInStep);
}

export function fadeOutEffect(target, duration, callback) {
    let opacity = 1;
    target.style.opacity = opacity;
    const startTime = performance.now();
    function fadeOutStep(currentTime) {
        opacity = Math.max(1 - (currentTime - startTime) / duration, 0);
        target.style.opacity = opacity;
        if (opacity > 0) {
            requestAnimationFrame(fadeOutStep);
        } else if (callback) {
            callback();
        }
    }
    requestAnimationFrame(fadeOutStep);
}
