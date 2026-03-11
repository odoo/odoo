/**
 * Grep `_detectNavbar`: the dynamic navbar's dropdown positioning was activated
 * to prevent sub-menus overflow. This positioning will use the default BS
 * offsets to position sub-menus leading to a small gap that hides them when
 * hovered (on "Hover" mode). The goal here is to prevent this offset when the
 * target is inside a navbar.
 */
const bsGetOffsetFunction = Dropdown.prototype._getOffset;
Dropdown.prototype._getOffset = function () {
    const offset = bsGetOffsetFunction.apply(this, arguments);
    if (this._element.closest(".o_hoverable_dropdown .navbar")) {
        return [offset[0], 0];
    }
    return offset;
};

/**
 * A "transitionend" event is set on the active carousel item when the carousel
 * is sliding. If the carousel is disposed while a transition is still
 * happening, the "transitionend" event will be triggered on the now-null
 * `this._element`, which can cause a crash. To prevent this, we preemptively
 * dispatch the "transitionend" event on the active slide item as it can
 * only be called once per transition.
 */
const bsCarouselDispose = window.Carousel.prototype.dispose;
window.Carousel.prototype.dispose = function () {
    if (this._isSliding) {
        this._getActive().dispatchEvent(new Event("transitionend"));
    }
    this._clearInterval();
    bsCarouselDispose.call(this);
};
