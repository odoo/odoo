/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import sOptions from "@web_editor/js/editor/snippets.options";

sOptions.registry.twitter = sOptions.Class.extend({
    /**
     * @override
     */
    start: function () {
        const configuration = document.createElement("button");
        configuration.classList.add("btn", "btn-primary", "d-none");
        configuration.setAttribute("type", "button");
        configuration.setAttribute("contenteditable", "false");

        const textElement = document.createElement("span");
        textElement.textContent = _t("Reload");
        configuration.appendChild(textElement);

        var div = document.createElement('div');
        document.body.appendChild(div);
        div.appendChild(configuration);
        configuration.addEventListener('click', function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            rpc('/website_twitter/reload');
        });
        this.$target.on('mouseover.website_twitter', function () {
            var $selected = $(this);
            var position = $selected.offset();
            configuration.classList.remove('d-none');
            setOffset(
                configuration,
                $selected.outerHeight() / 2
                    + position.top
                    - configuration.offsetHeight / 2,
                $selected.outerWidth() / 2
                    + position.left
                    - configuration.offsetWidth / 2
            );
        }).on('mouseleave.website_twitter', function (e) {
            if (isNaN(e.clientX) || isNaN(e.clientY)) {
                return;
            }
            var current = document.elementFromPoint(e.clientX, e.clientY);
            if (current === configuration) {
                return;
            }
            configuration.classList.add('d-none');
        });
        this.$target.on('click.website_twitter', '.lnk_configure', function (e) {
            window.location = e.currentTarget.href;
        });
        this.trigger_up('widgets_stop_request', {
            $target: this.$target,
        });
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    cleanForSave: function () {
        this.$target.find('.twitter_timeline').empty();
    },
    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        this.$target.off('.website_twitter');
    },
});

/**
 * Retrieves the current offset of an element relative to the document.
 *
 * @param {HTMLElement} element - The element whose offset is to be calculated.
 * @returns {object} An object containing the top and left offsets.
 */
function getOffset(element) {
    if (!element.getClientRects().length) {
        return { top: 0, left: 0 };
    } else {
        const rect = element.getBoundingClientRect();
        const win = element.ownerDocument.defaultView;
        return {
            top: rect.top + win.pageYOffset,
            left: rect.left + win.pageXOffset,
        };
    }
}

/**
 * Adjusts the position of an element relative to its offset parent or specified coordinates.
 *
 * @param {HTMLElement} element - The element whose position is to be adjusted.
 * @param {number} top - The new top position of the element.
 * @param {number} left - The new left position of the element.
 */
function setOffset(element, top, left) {
    const computedStyle = getComputedStyle(element);

    if (computedStyle.position === "static") {
        element.style.position = "relative";
    }

    const curOffset = getOffset(element);
    const curCSSTop = getComputedStyle(element).top;
    const curCSSLeft = getComputedStyle(element).left;

    let curLeft;
    let curTop;
    const props = {};

    if (
        (computedStyle.position === "absolute" || computedStyle.position === "fixed") &&
        (curCSSTop === "auto" || curCSSLeft === "auto")
    ) {
        const { top, left } = element.getBoundingClientRect();
        const { marginTop, marginLeft } = computedStyle;
        curTop = top - parseInt(marginTop, 10);
        curLeft = left - parseInt(marginLeft, 10);
    } else {
        curTop = parseFloat(curCSSTop) || 0;
        curLeft = parseFloat(curCSSLeft) || 0;
    }

    props.top = (top - curOffset.top) + curTop;
    props.left = (left - curOffset.left) + curLeft;
    Object.keys(props).forEach(function(key) {
        element.style[key] = props[key] + 'px';
    });
}
