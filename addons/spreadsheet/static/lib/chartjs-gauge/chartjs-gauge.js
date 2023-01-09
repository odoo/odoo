/*!
 * chartjs-gauge.js v0.3.0
 * https://github.com/haiiaaa/chartjs-gauge/
 * (c) 2021 chartjs-gauge.js Contributors
 * Released under the MIT License
 */
(function (global, factory) {
typeof exports === 'object' && typeof module !== 'undefined' ? module.exports = factory(require('chart.js')) :
typeof define === 'function' && define.amd ? define(['chart.js'], factory) :
(global = global || self, global.Gauge = factory(global.Chart));
}(this, (function (Chart) { 'use strict';

Chart = Chart && Object.prototype.hasOwnProperty.call(Chart, 'default') ? Chart['default'] : Chart;

function _defineProperty(obj, key, value) {
    if (key in obj) {
    Object.defineProperty(obj, key, {
        value: value,
        enumerable: true,
        configurable: true,
        writable: true
    });
    } else {
    obj[key] = value;
    }

    return obj;
}

function ownKeys(object, enumerableOnly) {
    var keys = Object.keys(object);

    if (Object.getOwnPropertySymbols) {
    var symbols = Object.getOwnPropertySymbols(object);
    if (enumerableOnly) symbols = symbols.filter(function (sym) {
        return Object.getOwnPropertyDescriptor(object, sym).enumerable;
    });
    keys.push.apply(keys, symbols);
    }

    return keys;
}

function _objectSpread2(target) {
    for (var i = 1; i < arguments.length; i++) {
    var source = arguments[i] != null ? arguments[i] : {};

    if (i % 2) {
        ownKeys(Object(source), true).forEach(function (key) {
        _defineProperty(target, key, source[key]);
        });
    } else if (Object.getOwnPropertyDescriptors) {
        Object.defineProperties(target, Object.getOwnPropertyDescriptors(source));
    } else {
        ownKeys(Object(source)).forEach(function (key) {
        Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key));
        });
    }
    }

    return target;
}

Chart.defaults._set('gauge', {
    needle: {
    // Needle circle radius as the percentage of the chart area width
    radiusPercentage: 2,
    // Needle width as the percentage of the chart area width
    widthPercentage: 3.2,
    // Needle length as the percentage of the interval between inner radius (0%) and outer radius (100%) of the arc
    lengthPercentage: 80,
    // The color of the needle
    color: 'rgba(0, 0, 0, 1)'
    },
    valueLabel: {
    // fontSize: undefined
    display: true,
    formatter: null,
    color: 'rgba(255, 255, 255, 1)',
    backgroundColor: 'rgba(0, 0, 0, 1)',
    borderRadius: 5,
    padding: {
        top: 5,
        right: 5,
        bottom: 5,
        left: 5
    },
    bottomMarginPercentage: 5
    },
    animation: {
    duration: 1000,
    animateRotate: true,
    animateScale: false
    },
    // The percentage of the chart that we cut out of the middle.
    cutoutPercentage: 50,
    // The rotation of the chart, where the first data arc begins.
    rotation: -Math.PI,
    // The total circumference of the chart.
    circumference: Math.PI,
    legend: {
    display: false
    },
    tooltips: {
    enabled: false
    }
});

var GaugeController = Chart.controllers.doughnut.extend({
    getValuePercent: function getValuePercent(_ref, value) {
    var minValue = _ref.minValue,
        data = _ref.data;
    var min = minValue || 0;
    var max = [undefined, null].includes(data[data.length - 1]) ? 1 : data[data.length - 1];
    var length = max - min;
    var percent = (value - min) / length;
    return percent;
    },
    getWidth: function getWidth(chart) {
    return chart.chartArea.right - chart.chartArea.left;
    },
    getTranslation: function getTranslation(chart) {
    var chartArea = chart.chartArea,
        offsetX = chart.offsetX,
        offsetY = chart.offsetY;
    var centerX = (chartArea.left + chartArea.right) / 2;
    var centerY = (chartArea.top + chartArea.bottom) / 2;
    var dx = centerX + offsetX;
    var dy = centerY + offsetY;
    return {
        dx: dx,
        dy: dy
    };
    },
    getAngle: function getAngle(_ref2) {
    var chart = _ref2.chart,
        valuePercent = _ref2.valuePercent;
    var _chart$options = chart.options,
        rotation = _chart$options.rotation,
        circumference = _chart$options.circumference;
    return rotation + circumference * valuePercent;
    },

    /* TODO set min padding, not applied until chart.update() (also chartArea must have been set)
    setBottomPadding(chart) {
    const needleRadius = this.getNeedleRadius(chart);
    const padding = this.chart.config.options.layout.padding;
    if (needleRadius > padding.bottom) {
        padding.bottom = needleRadius;
        return true;
    }
    return false;
    },
    */
    drawNeedle: function drawNeedle(ease) {
    if (!this.chart.animating) {
        // triggered when hovering
        ease = 1;
    }

    var _this$chart = this.chart,
        ctx = _this$chart.ctx,
        config = _this$chart.config,
        innerRadius = _this$chart.innerRadius,
        outerRadius = _this$chart.outerRadius;
    var dataset = config.data.datasets[this.index];

    var _this$getMeta = this.getMeta(),
        previous = _this$getMeta.previous;

    var _config$options$needl = config.options.needle,
        radiusPercentage = _config$options$needl.radiusPercentage,
        widthPercentage = _config$options$needl.widthPercentage,
        lengthPercentage = _config$options$needl.lengthPercentage,
        color = _config$options$needl.color;
    var width = this.getWidth(this.chart);
    var needleRadius = radiusPercentage / 100 * width;
    var needleWidth = widthPercentage / 100 * width;
    var needleLength = lengthPercentage / 100 * (outerRadius - innerRadius) + innerRadius; // center

    var _this$getTranslation = this.getTranslation(this.chart),
        dx = _this$getTranslation.dx,
        dy = _this$getTranslation.dy; // interpolate


    var origin = this.getAngle({
        chart: this.chart,
        valuePercent: previous.valuePercent
    }); // TODO valuePercent is in current.valuePercent also

    var target = this.getAngle({
        chart: this.chart,
        valuePercent: this.getValuePercent(dataset, dataset.value)
    });
    var angle = origin + (target - origin) * ease; // draw

    ctx.save();
    ctx.translate(dx, dy);
    ctx.rotate(angle);
    ctx.fillStyle = color; // draw circle

    ctx.beginPath();
    ctx.ellipse(0, 0, needleRadius, needleRadius, 0, 0, 2 * Math.PI);
    ctx.fill(); // draw needle

    ctx.beginPath();
    ctx.moveTo(0, needleWidth / 2);
    ctx.lineTo(needleLength, 0);
    ctx.lineTo(0, -needleWidth / 2);
    ctx.fill();
    ctx.restore();
    },
    drawValueLabel: function drawValueLabel(ease) {
    // eslint-disable-line no-unused-vars
    if (!this.chart.config.options.valueLabel.display) {
        return;
    }

    var _this$chart2 = this.chart,
        ctx = _this$chart2.ctx,
        config = _this$chart2.config;
    var defaultFontFamily = config.options.defaultFontFamily;
    var dataset = config.data.datasets[this.index];
    var _config$options$value = config.options.valueLabel,
        formatter = _config$options$value.formatter,
        fontSize = _config$options$value.fontSize,
        color = _config$options$value.color,
        backgroundColor = _config$options$value.backgroundColor,
        borderRadius = _config$options$value.borderRadius,
        padding = _config$options$value.padding,
        bottomMarginPercentage = _config$options$value.bottomMarginPercentage;
    var width = this.getWidth(this.chart);
    var bottomMargin = bottomMarginPercentage / 100 * width;

    var fmt = formatter || function (value) {
        return value;
    };

    var valueText = fmt(dataset.value).toString();
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'center';

    if (fontSize) {
        ctx.font = "".concat(fontSize, "px ").concat(defaultFontFamily);
    } // const { width: textWidth, actualBoundingBoxAscent, actualBoundingBoxDescent } = ctx.measureText(valueText);
    // const textHeight = actualBoundingBoxAscent + actualBoundingBoxDescent;


    var _ctx$measureText = ctx.measureText(valueText),
        textWidth = _ctx$measureText.width; // approximate height until browsers support advanced TextMetrics


    var textHeight = Math.max(ctx.measureText('m').width, ctx.measureText("\uFF37").width);
    var x = -(padding.left + textWidth / 2);
    var y = -(padding.top + textHeight / 2);
    var w = padding.left + textWidth + padding.right;
    var h = padding.top + textHeight + padding.bottom; // center

    var _this$getTranslation2 = this.getTranslation(this.chart),
        dx = _this$getTranslation2.dx,
        dy = _this$getTranslation2.dy; // add rotation


    var rotation = this.chart.options.rotation % (Math.PI * 2.0);
    dx += bottomMargin * Math.cos(rotation + Math.PI / 2);
    dy += bottomMargin * Math.sin(rotation + Math.PI / 2); // draw

    ctx.save();
    ctx.translate(dx, dy); // draw background

    ctx.beginPath();
    Chart.helpers.canvas.roundedRect(ctx, x, y, w, h, borderRadius);
    ctx.fillStyle = backgroundColor;
    ctx.fill(); // draw value text

    ctx.fillStyle = color || config.options.defaultFontColor;
    var magicNumber = 0.075; // manual testing

    ctx.fillText(valueText, 0, textHeight * magicNumber);
    ctx.restore();
    },
    // overrides
    update: function update(reset) {
    var dataset = this.chart.config.data.datasets[this.index];
    dataset.minValue = dataset.minValue || 0;
    var meta = this.getMeta();
    var initialValue = {
        valuePercent: 0
    }; // animations on will call update(reset) before update()

    if (reset) {
        meta.previous = null;
        meta.current = initialValue;
    } else {
        dataset.data.sort(function (a, b) {
        return a - b;
        });
        meta.previous = meta.current || initialValue;
        meta.current = {
        valuePercent: this.getValuePercent(dataset, dataset.value)
        };
    }

    Chart.controllers.doughnut.prototype.update.call(this, reset);
    },
    updateElement: function updateElement(arc, index, reset) {
    // TODO handle reset and options.animation
    Chart.controllers.doughnut.prototype.updateElement.call(this, arc, index, reset);
    var dataset = this.getDataset();
    var data = dataset.data; // const { options } = this.chart.config;
    // scale data

    var previousValue = index === 0 ? dataset.minValue : data[index - 1];
    var value = data[index];
    var startAngle = this.getAngle({
        chart: this.chart,
        valuePercent: this.getValuePercent(dataset, previousValue)
    });
    var endAngle = this.getAngle({
        chart: this.chart,
        valuePercent: this.getValuePercent(dataset, value)
    });
    var circumference = endAngle - startAngle;
    arc._model = _objectSpread2({}, arc._model, {
        startAngle: startAngle,
        endAngle: endAngle,
        circumference: circumference
    });
    },
    draw: function draw(ease) {
    Chart.controllers.doughnut.prototype.draw.call(this, ease);
    this.drawNeedle(ease);
    this.drawValueLabel(ease);
    }
});

/* eslint-disable max-len, func-names */
var polyfill = function polyfill() {
    if (CanvasRenderingContext2D.prototype.ellipse === undefined) {
    CanvasRenderingContext2D.prototype.ellipse = function (x, y, radiusX, radiusY, rotation, startAngle, endAngle, antiClockwise) {
        this.save();
        this.translate(x, y);
        this.rotate(rotation);
        this.scale(radiusX, radiusY);
        this.arc(0, 0, 1, startAngle, endAngle, antiClockwise);
        this.restore();
    };
    }
};

polyfill();
Chart.controllers.gauge = GaugeController;

Chart.Gauge = function (context, config) {
    config.type = 'gauge';
    return new Chart(context, config);
};

var index = Chart.Gauge;

return index;

})));
