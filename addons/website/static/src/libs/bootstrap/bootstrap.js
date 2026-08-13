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
