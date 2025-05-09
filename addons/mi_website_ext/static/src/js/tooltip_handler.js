/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.TooltipHandler = publicWidget.Widget.extend({
  selector: ".benefits-card",

  events: {
    "mouseenter img.tooltip-img": "_showTooltip",
    "mouseleave img.tooltip-img": "_hideTooltip",
    "mousemove img.tooltip-img": "_moveTooltip",
  },

  start: function () {
    this._createTooltipElement();
    return this._super(...arguments);
  },

  _createTooltipElement: function () {
    this.$tooltip = $(`
            <div class="custom-tooltip o_technical_modal" style="display:none;">
                <div class="tooltip-content"">
                    <img class="tooltip-icon" src="" alt="tooltip icon" />
                    <div class="tooltip-info">
                    <h4 class="tooltip-title"></h4>
                    <p class="tooltip-text"></p>
                    </div>
                </div>
            </div>
        `);
    $("body").append(this.$tooltip);
  },

  _showTooltip: function (ev) {
    const $img = $(ev.currentTarget);
    const text = $img.data("tooltip-text");
    const icon = $img.data("tooltip-icon");
    const title = $img.data("tooltip-title");

    this.$tooltip.find(".tooltip-icon").attr("src", icon);
    this.$tooltip.find(".tooltip-text").text(text);
    this.$tooltip.find(".tooltip-title").text(title);
    this.$tooltip.show();
    this._moveTooltip(ev); // posicionar al aparecer
  },

  _hideTooltip: function () {
    this.$tooltip.hide();
  },

  _moveTooltip: function (ev) {
    this.$tooltip.css({
      top: ev.pageY - 120 + "px",
      left: ev.pageX + 20 + "px",
    });
  },
});
