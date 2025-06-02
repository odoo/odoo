/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.TooltipHandler = publicWidget.Widget.extend({
    selector: ".benefits-card",

    start: function () {
        this._tooltipTimeout = null;

        this.$tooltip = $(`
            <div class="custom-tooltip o_technical_modal" style="display:none; transition: opacity 0.3s ease;">
                <div class="tooltip-content">
                    <img class="tooltip-icon" src="" alt="tooltip icon" />
                    <div class="tooltip-info">
                        <h4 class="tooltip-title"></h4>
                        <p class="tooltip-text"></p>
                    </div>
                </div>
            </div>
        `).appendTo('body');

        this.$el.on('mouseenter', 'img.tooltip-img', this._onMouseEnter.bind(this));
        this.$el.on('mouseleave', 'img.tooltip-img', this._onMouseLeave.bind(this));
        this.$tooltip.on('mouseenter', this._cancelHideTooltip.bind(this));
        this.$tooltip.on('mouseleave', this._hideTooltip.bind(this));

        return this._super(...arguments);
    },

    _onMouseEnter: function (ev) {
        clearTimeout(this._tooltipTimeout);
        const $img = $(ev.currentTarget);
        const title = $img.data('tooltip-title') || '';
        const text = $img.data('tooltip-text') || '';
        const icon = $img.data('tooltip-icon') || '';

        this.$tooltip.find(".tooltip-title").text(title);
        this.$tooltip.find(".tooltip-text").text(text);
        this.$tooltip.find(".tooltip-icon").attr("src", icon);
        this.$tooltip.css({ display: 'block', opacity: 0 });

        const offset = $img.offset();
        const tooltipHeight = this.$tooltip.outerHeight();
        const left = offset.left + $img.outerWidth() + 32; // 12px de espacio entre el icono y el tooltip
        const top = offset.top + ($img.outerHeight() / 2) - (tooltipHeight / 2); // centrar verticalmente respecto al badge

        this.$tooltip.css({
            top: `${top}px`,
            left: `${left}px`,
            opacity: 1,
            zIndex: 9999,
        });
    },

    _onMouseLeave: function () {
        this._tooltipTimeout = setTimeout(() => {
            this.$tooltip.css({ opacity: 0 });
            setTimeout(() => this.$tooltip.hide(), 300);
        }, 150);
    },

    _cancelHideTooltip: function () {
        clearTimeout(this._tooltipTimeout);
        this.$tooltip.css({ opacity: 1 }).show();
    },

    _hideTooltip: function () {
        this.$tooltip.css({ opacity: 0 });
        setTimeout(() => this.$tooltip.hide(), 300);
    },
});
