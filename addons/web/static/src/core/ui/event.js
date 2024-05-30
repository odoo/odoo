const fn = function (e, selector, handler) {
    let target = e.target;
    if (typeof selector === "string") {
        while (!target.matches(selector) && target !== this) {
            target = target.parentElement;
        }

        if (target.matches(selector)) {
            handler.call(target, e);
        }
    } else {
        selector.call(this, e);
    }
};

HTMLElement.prototype.on = function (event, selector, handler) {
    this.addEventListener(event, fn.bind(selector, handler));
};

HTMLElement.prototype.off = function (event) {
    this.removeEventListener(event, fn);
};
