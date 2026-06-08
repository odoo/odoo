/*!
 * chartjs-chart-treemap v3.1.0
 * https://chartjs-chart-treemap.pages.dev/
 * (c) 2025 Jukka Kurkela
 * Released under the MIT license
 */
(function (global, factory) {
    typeof exports === "object" && typeof module !== "undefined"
      ? factory(exports, require("chart.js"), require("chart.js/helpers"))
      : typeof define === "function" && define.amd
      ? define(["exports", "chart.js", "chart.js/helpers"], factory)
      : ((global = typeof globalThis !== "undefined" ? globalThis : global || self),
        factory((global["chartjs-chart-treemap"] = {}), global.Chart, global.Chart.helpers));
  })(this, function (exports, chart_js, helpers) {
    "use strict";

    const isOlderPart = (act, req) =>
      req > act || (act.length > req.length && act.slice(0, req.length) === req);

    const getGroupKey = (lvl) => "" + lvl;

    function scanTreeObject(keys, treeLeafKey, obj, tree = [], lvl = 0, result = []) {
      const objIndex = lvl - 1;
      if (keys[0] in obj && lvl > 0) {
        const record = tree.reduce(function (reduced, item, i) {
          if (i !== objIndex) {
            reduced[getGroupKey(i)] = item;
          }
          return reduced;
        }, {});
        record[treeLeafKey] = tree[objIndex];
        keys.forEach(function (k) {
          record[k] = obj[k];
        });
        result.push(record);
      } else {
        for (const childKey of Object.keys(obj)) {
          const child = obj[childKey];
          if (helpers.isObject(child)) {
            tree.push(childKey);
            scanTreeObject(keys, treeLeafKey, child, tree, lvl + 1, result);
          }
        }
      }
      tree.splice(objIndex, 1);
      return result;
    }

    function normalizeTreeToArray(keys, treeLeafKey, obj) {
      const data = scanTreeObject(keys, treeLeafKey, obj);
      if (!data.length) {
        return data;
      }
      const max = data.reduce(function (maxVal, element) {
        // minus 2 because _leaf and value properties are added
        // on top to groups ones
        const ikeys = Object.keys(element).length - 2;
        return maxVal > ikeys ? maxVal : ikeys;
      });
      data.forEach(function (element) {
        for (let i = 0; i < max; i++) {
          const groupKey = getGroupKey(i);
          if (!element[groupKey]) {
            element[groupKey] = "";
          }
        }
      });
      return data;
    }

    // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/flat
    function flatten(input) {
      const stack = [...input];
      const res = [];
      while (stack.length) {
        // pop value from stack
        const next = stack.pop();
        if (Array.isArray(next)) {
          // push back array items, won't modify the original input
          stack.push(...next);
        } else {
          res.push(next);
        }
      }
      // reverse to restore input order
      return res.reverse();
    }

    function getPath(groups, value, defaultValue) {
      if (!groups.length) {
        return;
      }
      const path = [];
      for (const grp of groups) {
        const item = value[grp];
        if (item === "") {
          path.push(defaultValue);
          break;
        }
        path.push(item);
      }
      return path.length ? path.join(".") : defaultValue;
    }

    /**
     * @param {[]} values
     * @param {string} grp
     * @param {[string]} keys
     * @param {string} treeeLeafKey
     * @param {string} [mainGrp]
     * @param {*} [mainValue]
     * @param {[]} groups
     */
    function group(values, grp, keys, treeLeafKey, mainGrp, mainValue, groups = []) {
      const key = keys[0];
      const addKeys = keys.slice(1);
      const tmp = Object.create(null);
      const data = Object.create(null);
      const ret = [];
      let g, i, n;
      for (i = 0, n = values.length; i < n; ++i) {
        const v = values[i];
        if (mainGrp && v[mainGrp] !== mainValue) {
          continue;
        }
        g = v[grp] || v[treeLeafKey] || "";
        if (!g) {
          return [];
        }
        if (!(g in tmp)) {
          const tmpRef = (tmp[g] = { value: 0 });
          addKeys.forEach(function (k) {
            tmpRef[k] = 0;
          });
          data[g] = [];
        }
        tmp[g].value += +v[key];
        tmp[g].label = v[grp] || "";
        const tmpRef = tmp[g];
        addKeys.forEach(function (k) {
          tmpRef[k] += v[k];
        });
        tmp[g].path = getPath(groups, v, g);
        data[g].push(v);
      }

      Object.keys(tmp).forEach((k) => {
        const v = { children: data[k] };
        v[key] = +tmp[k].value;
        addKeys.forEach(function (ak) {
          v[ak] = +tmp[k][ak];
        });
        v[grp] = tmp[k].label;
        v.label = k;
        v.path = tmp[k].path;

        if (mainGrp) {
          v[mainGrp] = mainValue;
        }
        ret.push(v);
      });

      return ret;
    }

    function index(values, key) {
      let n = values.length;
      let i;

      if (!n) {
        return key;
      }

      const obj = helpers.isObject(values[0]);
      key = obj ? key : "v";

      for (i = 0, n = values.length; i < n; ++i) {
        if (obj) {
          values[i]._idx = i;
        } else {
          values[i] = { v: values[i], _idx: i };
        }
      }
      return key;
    }

    function sort(values, key) {
      if (key) {
        values.sort((a, b) => +b[key] - +a[key]);
      } else {
        values.sort((a, b) => +b - +a);
      }
    }

    function sum(values, key) {
      let s, i, n;

      for (s = 0, i = 0, n = values.length; i < n; ++i) {
        s += key ? +values[i][key] : +values[i];
      }

      return s;
    }

    /**
     * @param {string} pkg
     * @param {string} min
     * @param {string} ver
     * @param {boolean} [strict=true]
     * @returns {boolean}
     */
    function requireVersion(pkg, min, ver, strict = true) {
      const parts = ver.split(".");
      let i = 0;
      for (const req of min.split(".")) {
        const act = parts[i++];
        if (parseInt(req, 10) < parseInt(act, 10)) {
          break;
        }
        if (isOlderPart(act, req)) {
          if (strict) {
            throw new Error(`${pkg} v${ver} is not supported. v${min} or newer is required.`);
          } else {
            return false;
          }
        }
      }
      return true;
    }

    const widthCache = new Map();

    /**
     * Helper function to get the bounds of the rect
     * @param {TreemapElement} rect the rect
     * @param {boolean} [useFinalPosition]
     * @return {object} bounds of the rect
     * @private
     */
    function getBounds(rect, useFinalPosition) {
      const { x, y, width, height } = rect.getProps(["x", "y", "width", "height"], useFinalPosition);
      return { left: x, top: y, right: x + width, bottom: y + height };
    }

    function limit(value, min, max) {
      return Math.max(Math.min(value, max), min);
    }

    function parseBorderWidth(value, maxW, maxH) {
      const o = helpers.toTRBL(value);

      return {
        t: limit(o.top, 0, maxH),
        r: limit(o.right, 0, maxW),
        b: limit(o.bottom, 0, maxH),
        l: limit(o.left, 0, maxW),
      };
    }

    function parseBorderRadius(value, maxW, maxH) {
      const o = helpers.toTRBLCorners(value);
      const maxR = Math.min(maxW, maxH);

      return {
        topLeft: limit(o.topLeft, 0, maxR),
        topRight: limit(o.topRight, 0, maxR),
        bottomLeft: limit(o.bottomLeft, 0, maxR),
        bottomRight: limit(o.bottomRight, 0, maxR),
      };
    }

    function boundingRects(rect) {
      const bounds = getBounds(rect);
      const width = bounds.right - bounds.left;
      const height = bounds.bottom - bounds.top;
      const border = parseBorderWidth(rect.options.borderWidth, width / 2, height / 2);
      const radius = parseBorderRadius(rect.options.borderRadius, width / 2, height / 2);
      const outer = {
        x: bounds.left,
        y: bounds.top,
        w: width,
        h: height,
        active: rect.active,
        radius,
      };

      return {
        outer,
        inner: {
          x: outer.x + border.l,
          y: outer.y + border.t,
          w: outer.w - border.l - border.r,
          h: outer.h - border.t - border.b,
          active: rect.active,
          radius: {
            topLeft: Math.max(0, radius.topLeft - Math.max(border.t, border.l)),
            topRight: Math.max(0, radius.topRight - Math.max(border.t, border.r)),
            bottomLeft: Math.max(0, radius.bottomLeft - Math.max(border.b, border.l)),
            bottomRight: Math.max(0, radius.bottomRight - Math.max(border.b, border.r)),
          },
        },
      };
    }

    function inRange(rect, x, y, useFinalPosition) {
      const skipX = x === null;
      const skipY = y === null;
      const bounds = !rect || (skipX && skipY) ? false : getBounds(rect, useFinalPosition);

      return (
        bounds &&
        (skipX || (x >= bounds.left && x <= bounds.right)) &&
        (skipY || (y >= bounds.top && y <= bounds.bottom))
      );
    }

    function hasRadius(radius) {
      return radius.topLeft || radius.topRight || radius.bottomLeft || radius.bottomRight;
    }

    /**
     * Add a path of a rectangle to the current sub-path
     * @param {CanvasRenderingContext2D} ctx Context
     * @param {*} rect Bounding rect
     */
    function addNormalRectPath(ctx, rect) {
      ctx.rect(rect.x, rect.y, rect.w, rect.h);
    }

    function shouldDrawCaption(displayMode, rect, options) {
      if (!options || options.display === false) {
        return false;
      }
      if (displayMode === "headerBoxes") {
        return true;
      }
      const { w, h } = rect;
      const font = helpers.toFont(options.font);
      const min = font.lineHeight;
      const padding = limit(helpers.valueOrDefault(options.padding, 3) * 2, 0, Math.min(w, h));
      return w - padding > min && h - padding > min;
    }

    function getCaptionHeight(displayMode, rect, font, padding) {
      if (displayMode !== "headerBoxes") {
        return font.lineHeight + padding * 2;
      }
      const captionHeight = font.lineHeight + padding * 2;
      return rect.h < 2 * captionHeight ? rect.h / 3 : captionHeight;
    }

    function drawText(ctx, rect, options, item) {
      const { captions, labels, displayMode } = options;
      ctx.save();
      ctx.beginPath();
      ctx.rect(rect.x, rect.y, rect.w, rect.h);
      ctx.clip();
      const isLeaf = item && (!helpers.defined(item.l) || item.isLeaf);
      if (isLeaf && labels.display) {
        drawLabel(ctx, rect, options);
      } else if (!isLeaf && shouldDrawCaption(displayMode, rect, captions)) {
        drawCaption(ctx, rect, options, item);
      }
      ctx.restore();
    }

    function drawCaption(ctx, rect, options, item) {
      const { captions, spacing, rtl, displayMode } = options;
      const { color, hoverColor, font, hoverFont, padding, align, formatter } = captions;
      const oColor = (rect.active ? hoverColor : color) || color;
      const oAlign = align || (rtl ? "right" : "left");
      const optFont = (rect.active ? hoverFont : font) || font;
      const oFont = helpers.toFont(optFont);
      const fonts = [oFont];
      if (oFont.lineHeight > rect.h) {
        return;
      }
      let text = formatter || item.g;
      const captionSize = measureLabelSize(ctx, [formatter], fonts);
      if (captionSize.width + 2 * padding > rect.w) {
        text = sliceTextToFitWidth(ctx, text, rect.w - 2 * padding, fonts);
      }

      const lh = oFont.lineHeight / 2;
      const x = calculateX(rect, oAlign, padding);
      ctx.fillStyle = oColor;
      ctx.font = oFont.string;
      ctx.textAlign = oAlign;
      ctx.textBaseline = "middle";
      const y = displayMode === "headerBoxes" ? rect.y + rect.h / 2 : rect.y + padding + spacing + lh;
      ctx.fillText(text, x, y);
    }

    function sliceTextToFitWidth(ctx, text, width, fonts) {
      const ellipsis = "...";
      const ellipsisWidth = measureLabelSize(ctx, [ellipsis], fonts).width;
      if (ellipsisWidth >= width) {
        return "";
      }
      let lowerBoundLen = 1;
      let upperBoundLen = text.length;
      let currentWidth;
      while (lowerBoundLen <= upperBoundLen) {
        const currentLen = Math.floor((lowerBoundLen + upperBoundLen) / 2);
        const currentText = text.slice(0, currentLen);
        currentWidth = measureLabelSize(ctx, [currentText], fonts).width;
        if (currentWidth + ellipsisWidth > width) {
          upperBoundLen = currentLen - 1;
        } else {
          lowerBoundLen = currentLen + 1;
        }
      }
      const slicedText = text.slice(0, Math.max(0, lowerBoundLen - 1));
      return slicedText ? slicedText + ellipsis : "";
    }

    function measureLabelSize(ctx, lines, fonts) {
      const fontsKey = fonts.reduce(function (prev, item) {
        prev += item.string;
        return prev;
      }, "");
      const mapKey = lines.join() + fontsKey + (ctx._measureText ? "-spriting" : "");
      if (!widthCache.has(mapKey)) {
        ctx.save();
        const count = lines.length;
        let width = 0;
        let height = 0;
        for (let i = 0; i < count; i++) {
          const font = fonts[Math.min(i, fonts.length - 1)];
          ctx.font = font.string;
          const text = lines[i];
          width = Math.max(width, ctx.measureText(text).width);
          height += font.lineHeight;
        }
        ctx.restore();
        widthCache.set(mapKey, { width, height });
      }
      return widthCache.get(mapKey);
    }

    function toFonts(fonts, fitRatio) {
      return fonts.map(function (f) {
        f.size = Math.floor(f.size * fitRatio);
        f.lineHeight = undefined;
        return helpers.toFont(f);
      });
    }

    function labelToDraw(ctx, rect, options, labelSize) {
      const { overflow, padding } = options;
      const { width, height } = labelSize;
      if (overflow === "hidden") {
        return !(width + padding * 2 > rect.w || height + padding * 2 > rect.h);
      } else if (overflow === "fit") {
        const ratio = Math.min(rect.w / (width + padding * 2), rect.h / (height + padding * 2));
        if (ratio < 1) {
          return ratio;
        }
      }
      return true;
    }

    function getFontFromOptions(rect, labels) {
      const { font, hoverFont } = labels;
      const optFont = (rect.active ? hoverFont : font) || font;
      return helpers.isArray(optFont)
        ? optFont.map((f) => helpers.toFont(f))
        : [helpers.toFont(optFont)];
    }

    function drawLabel(ctx, rect, options) {
      const labels = options.labels;
      const content = labels.formatter;
      if (!content) {
        return;
      }
      const contents = helpers.isArray(content) ? content : [content];
      let fonts = getFontFromOptions(rect, labels);
      let labelSize = measureLabelSize(ctx, contents, fonts);
      const lblToDraw = labelToDraw(ctx, rect, labels, labelSize);
      if (!lblToDraw) {
        return;
      }
      if (helpers.isNumber(lblToDraw)) {
        labelSize = { width: labelSize.width * lblToDraw, height: labelSize.height * lblToDraw };
        fonts = toFonts(fonts, lblToDraw);
      }
      const { color, hoverColor, align } = labels;
      const optColor = (rect.active ? hoverColor : color) || color;
      const colors = helpers.isArray(optColor) ? optColor : [optColor];
      const xyPoint = calculateXYLabel(rect, labels, labelSize);
      ctx.textAlign = align;
      ctx.textBaseline = "middle";
      let lhs = 0;
      contents.forEach(function (l, i) {
        const c = colors[Math.min(i, colors.length - 1)];
        const f = fonts[Math.min(i, fonts.length - 1)];
        const lh = f.lineHeight;
        ctx.font = f.string;
        ctx.fillStyle = c;
        ctx.fillText(l, xyPoint.x, xyPoint.y + lh / 2 + lhs);
        lhs += lh;
      });
    }

    function drawDivider(ctx, rect, options, item) {
      const dividers = options.dividers;
      if (!dividers.display || !item._data.children.length) {
        return;
      }
      const { x, y, w, h } = rect;
      const { lineColor, lineCapStyle, lineDash, lineDashOffset, lineWidth } = dividers;
      ctx.save();
      ctx.strokeStyle = lineColor;
      ctx.lineCap = lineCapStyle;
      ctx.setLineDash(lineDash);
      ctx.lineDashOffset = lineDashOffset;
      ctx.lineWidth = lineWidth;
      ctx.beginPath();
      if (w > h) {
        const w2 = w / 2;
        ctx.moveTo(x + w2, y);
        ctx.lineTo(x + w2, y + h);
      } else {
        const h2 = h / 2;
        ctx.moveTo(x, y + h2);
        ctx.lineTo(x + w, y + h2);
      }
      ctx.stroke();
      ctx.restore();
    }

    function calculateXYLabel(rect, options, labelSize) {
      const { align, position, padding } = options;
      let x, y;
      x = calculateX(rect, align, padding);
      if (position === "top") {
        y = rect.y + padding;
      } else if (position === "bottom") {
        y = rect.y + rect.h - padding - labelSize.height;
      } else {
        y = rect.y + (rect.h - labelSize.height) / 2 + padding;
      }
      return { x, y };
    }

    function calculateX(rect, align, padding) {
      if (align === "left") {
        return rect.x + padding;
      } else if (align === "right") {
        return rect.x + rect.w - padding;
      }
      return rect.x + rect.w / 2;
    }

    class TreemapElement extends chart_js.Element {
      constructor(cfg) {
        super();

        this.options = undefined;
        this.width = undefined;
        this.height = undefined;

        if (cfg) {
          Object.assign(this, cfg);
        }
      }

      draw(ctx, data) {
        if (!data) {
          return;
        }
        const options = this.options;
        const { inner, outer } = boundingRects(this);

        const addRectPath = hasRadius(outer.radius) ? helpers.addRoundedRectPath : addNormalRectPath;

        ctx.save();

        if (outer.w !== inner.w || outer.h !== inner.h) {
          ctx.beginPath();
          addRectPath(ctx, outer);
          ctx.clip();
          addRectPath(ctx, inner);
          ctx.fillStyle = options.borderColor;
          ctx.fill("evenodd");
        }

        ctx.beginPath();
        addRectPath(ctx, inner);
        ctx.fillStyle = options.backgroundColor;
        ctx.fill();

        drawDivider(ctx, inner, options, data);
        drawText(ctx, inner, options, data);
        ctx.restore();
      }

      inRange(mouseX, mouseY, useFinalPosition) {
        return inRange(this, mouseX, mouseY, useFinalPosition);
      }

      inXRange(mouseX, useFinalPosition) {
        return inRange(this, mouseX, null, useFinalPosition);
      }

      inYRange(mouseY, useFinalPosition) {
        return inRange(this, null, mouseY, useFinalPosition);
      }

      getCenterPoint(useFinalPosition) {
        const { x, y, width, height } = this.getProps(
          ["x", "y", "width", "height"],
          useFinalPosition
        );
        return {
          x: x + width / 2,
          y: y + height / 2,
        };
      }

      tooltipPosition() {
        return this.getCenterPoint();
      }

      /**
       * @todo: remove this unused function in v3
       */
      getRange(axis) {
        return axis === "x" ? this.width / 2 : this.height / 2;
      }
    }

    TreemapElement.id = "treemap";

    TreemapElement.defaults = {
      borderRadius: 0,
      borderWidth: 0,
      captions: {
        align: undefined,
        color: "black",
        display: true,
        font: {},
        formatter: (ctx) => ctx.raw.g || ctx.raw._data.label || "",
        padding: 3,
      },
      dividers: {
        display: false,
        lineCapStyle: "butt",
        lineColor: "black",
        lineDash: [],
        lineDashOffset: 0,
        lineWidth: 1,
      },
      label: undefined,
      labels: {
        align: "center",
        color: "black",
        display: false,
        font: {},
        formatter(ctx) {
          if (ctx.raw.g) {
            return [ctx.raw.g, ctx.raw.v + ""];
          }
          return ctx.raw._data.label ? [ctx.raw._data.label, ctx.raw.v + ""] : ctx.raw.v + "";
        },
        overflow: "cut",
        position: "middle",
        padding: 3,
      },
      rtl: false,
      spacing: 0.5,
      unsorted: false,
      displayMode: "containerBoxes",
    };

    TreemapElement.descriptors = {
      captions: {
        _fallback: true,
      },
      labels: {
        _fallback: true,
      },
      _scriptable: true,
      _indexable: false,
    };

    TreemapElement.defaultRoutes = {
      backgroundColor: "backgroundColor",
      borderColor: "borderColor",
    };

    function getDims(itm, w2, s2, key) {
      const a = itm._normalized;
      const ar = (w2 * a) / s2;
      const d1 = Math.sqrt(a * ar);
      const d2 = a / d1;
      const w = key === "_ix" ? d1 : d2;
      const h = key === "_ix" ? d2 : d1;

      return { d1, d2, w, h };
    }

    const getX = (rect, w) => (rect.rtl ? rect.x + rect.iw - w : rect.x + rect._ix);

    function buildRow(rect, itm, dims, sum) {
      const r = {
        x: getX(rect, dims.w),
        y: rect.y + rect._iy,
        w: dims.w,
        h: dims.h,
        a: itm._normalized,
        v: itm.value,
        vs: itm.values,
        s: sum,
        _data: itm._data,
      };
      if (itm.group) {
        r.g = itm.group;
        r.l = itm.level;
        r.gs = itm.groupSum;
      }
      return r;
    }

    class Rect {
      constructor(r) {
        r = r || { w: 1, h: 1 };
        this.rtl = !!r.rtl;
        this.unsorted = !!r.unsorted;
        this.x = r.x || r.left || 0;
        this.y = r.y || r.top || 0;
        this._ix = 0;
        this._iy = 0;
        this.w = r.w || r.width || r.right - r.left;
        this.h = r.h || r.height || r.bottom - r.top;
      }

      get area() {
        return this.w * this.h;
      }

      get iw() {
        return this.w - this._ix;
      }

      get ih() {
        return this.h - this._iy;
      }

      get dir() {
        const ih = this.ih;
        return ih <= this.iw && ih > 0 ? "y" : "x";
      }

      get side() {
        return this.dir === "x" ? this.iw : this.ih;
      }

      map(arr) {
        const { dir, side } = this;
        const key = dir === "x" ? "_ix" : "_iy";
        const sum = arr.nsum;
        const row = arr.get();
        const w2 = side * side;
        const s2 = sum * sum;
        const ret = [];
        let maxd2 = 0;
        let totd1 = 0;
        for (const itm of row) {
          const dims = getDims(itm, w2, s2, key);
          totd1 += dims.d1;
          maxd2 = Math.max(maxd2, dims.d2);
          ret.push(buildRow(this, itm, dims, arr.sum));
          this[key] += dims.d1;
        }

        this[dir === "x" ? "_iy" : "_ix"] += maxd2;
        this[key] -= totd1;
        return ret;
      }
    }

    const min = Math.min;
    const max = Math.max;

    function getStat(sa) {
      return {
        min: sa.min,
        max: sa.max,
        sum: sa.sum,
        nmin: sa.nmin,
        nmax: sa.nmax,
        nsum: sa.nsum,
      };
    }

    function getNewStat(sa, o) {
      const v = +o[sa.key];
      const n = v * sa.ratio;
      o._normalized = n;

      return {
        min: min(sa.min, v),
        max: max(sa.max, v),
        sum: sa.sum + v,
        nmin: min(sa.nmin, n),
        nmax: max(sa.nmax, n),
        nsum: sa.nsum + n,
      };
    }

    function setStat(sa, stat) {
      Object.assign(sa, stat);
    }

    function push(sa, o, stat) {
      sa._arr.push(o);
      setStat(sa, stat);
    }

    class StatArray {
      constructor(key, ratio) {
        const me = this;
        me.key = key;
        me.ratio = ratio;
        me.reset();
      }

      get length() {
        return this._arr.length;
      }

      reset() {
        const me = this;
        me._arr = [];
        me._hist = [];
        me.sum = 0;
        me.nsum = 0;
        me.min = Infinity;
        me.max = -Infinity;
        me.nmin = Infinity;
        me.nmax = -Infinity;
      }

      push(o) {
        push(this, o, getNewStat(this, o));
      }

      pushIf(o, fn, ...args) {
        const nstat = getNewStat(this, o);
        if (!fn(getStat(this), nstat, args)) {
          return o;
        }
        push(this, o, nstat);
      }

      get() {
        return this._arr;
      }
    }

    function compareAspectRatio(oldStat, newStat, args) {
      if (oldStat.sum === 0) {
        return true;
      }

      const [length] = args;
      const os2 = oldStat.nsum * oldStat.nsum;
      const ns2 = newStat.nsum * newStat.nsum;
      const l2 = length * length;
      const or = Math.max((l2 * oldStat.nmax) / os2, os2 / (l2 * oldStat.nmin));
      const nr = Math.max((l2 * newStat.nmax) / ns2, ns2 / (l2 * newStat.nmin));
      return nr <= or;
    }

    /**
     *
     * @param {number[]|object[]} values
     * @param {object} rectangle
     * @param {string} [key]
     * @param {string} [grp]
     * @param {number} [lvl]
     * @param {number} [gsum]
     */
    function squarify(values, rectangle, keys = [], grp, lvl, gsum) {
      values = values || [];
      const rows = [];
      const rect = new Rect(rectangle);
      const row = new StatArray("value", rect.area / sum(values, keys[0]));
      let length = rect.side;
      const n = values.length;
      let i, o;

      if (!n) {
        return rows;
      }

      const tmp = values.slice();
      let key = index(tmp, keys[0]);

      if (!rectangle?.unsorted) {
        sort(tmp, key);
      }

      const val = (idx) => (key ? +tmp[idx][key] : +tmp[idx]);
      const gval = (idx) => grp && tmp[idx][grp];

      for (i = 0; i < n; ++i) {
        o = {
          value: val(i),
          groupSum: gsum,
          _data: values[tmp[i]._idx],
          level: undefined,
          group: undefined,
        };
        if (grp) {
          o.level = lvl;
          o.group = gval(i);
          const tmpRef = tmp[i];
          o.values = keys.reduce(function (obj, k) {
            obj[k] = +tmpRef[k];
            return obj;
          }, {});
        }
        o = row.pushIf(o, compareAspectRatio, length);
        if (o) {
          rows.push(rect.map(row));
          length = rect.side;
          row.reset();
          row.push(o);
        }
      }
      if (row.length) {
        rows.push(rect.map(row));
      }
      return flatten(rows);
    }

    var version = "3.1.0";

    function scaleRect(sq, xScale, yScale, sp) {
      const sp2 = sp * 2;
      const x = xScale.getPixelForValue(sq.x);
      const y = yScale.getPixelForValue(sq.y);
      const w = xScale.getPixelForValue(sq.x + sq.w) - x;
      const h = yScale.getPixelForValue(sq.y + sq.h) - y;
      return {
        x: x + sp,
        y: y + sp,
        width: w - sp2,
        height: h - sp2,
        hidden: sp2 > w || sp2 > h,
      };
    }

    function rectNotEqual(r1, r2) {
      return (
        !r1 ||
        !r2 ||
        r1.x !== r2.x ||
        r1.y !== r2.y ||
        r1.w !== r2.w ||
        r1.h !== r2.h ||
        r1.rtl !== r2.rtl ||
        r1.unsorted !== r2.unsorted
      );
    }

    function arrayNotEqual(a, b) {
      let i, n;

      if (!a || !b) {
        return true;
      }

      if (a === b) {
        return false;
      }

      if (a.length !== b.length) {
        return true;
      }

      for (i = 0, n = a.length; i < n; ++i) {
        if (a[i] !== b[i]) {
          return true;
        }
      }
      return false;
    }

    function buildData(tree, dataset, keys, mainRect) {
      const treeLeafKey = dataset.treeLeafKey || "_leaf";
      if (helpers.isObject(tree)) {
        tree = normalizeTreeToArray(keys, treeLeafKey, tree);
      }
      const groups = dataset.groups || [];
      const glen = groups.length;
      const sp =
        dataset.displayMode === "headerBoxes" ? 0 : helpers.valueOrDefault(dataset.spacing, 0);
      const captions = dataset.captions || {};
      const font = helpers.toFont(captions.font);
      const padding = helpers.valueOrDefault(captions.padding, 3);

      function recur(treeElements, gidx, rect, parent, gs) {
        const g = getGroupKey(groups[gidx]);
        const pg = gidx > 0 && getGroupKey(groups[gidx - 1]);
        const gdata = group(
          treeElements,
          g,
          keys,
          treeLeafKey,
          pg,
          parent,
          groups.filter((item, index) => index <= gidx)
        );
        const gsq = squarify(gdata, rect, keys, g, gidx, gs);
        const ret = gsq.slice();
        if (gidx < glen - 1) {
          gsq.forEach((sq) => {
            const bw =
              dataset.displayMode === "headerBoxes"
                ? { l: 0, r: 0, t: 0, b: 0 }
                : parseBorderWidth(dataset.borderWidth, sq.w / 2, sq.h / 2);
            const subRect = {
              ...rect,
              x: sq.x + sp + bw.l,
              y: sq.y + sp + bw.t,
              w: sq.w - 2 * sp - bw.l - bw.r,
              h: sq.h - 2 * sp - bw.t - bw.b,
            };
            if (shouldDrawCaption(dataset.displayMode, subRect, captions)) {
              const captionHeight = getCaptionHeight(dataset.displayMode, subRect, font, padding);
              subRect.y += captionHeight;
              subRect.h -= captionHeight;
            }
            const children = [];
            gdata.forEach((gEl) => {
              children.push(...recur(gEl.children, gidx + 1, subRect, sq.g, sq.s));
            });
            ret.push(...children);
            sq.isLeaf = !children.length;
          });
        } else {
          gsq.forEach((sq) => {
            sq.isLeaf = true;
          });
        }
        return ret;
      }

      const result = glen ? recur(tree, 0, mainRect) : squarify(tree, mainRect, keys);
      return result
        .map((d) => {
          if (dataset.displayMode !== "headerBoxes" || d.isLeaf) {
            return d;
          }
          if (!shouldDrawCaption(dataset.displayMode, d, captions)) {
            return undefined;
          }
          const captionHeight = getCaptionHeight(dataset.displayMode, d, font, padding);
          return { ...d, h: captionHeight };
        })
        .filter((d) => d);
    }

    class TreemapController extends chart_js.DatasetController {
      constructor(chart, datasetIndex) {
        super(chart, datasetIndex);

        this._groups = undefined;
        this._keys = undefined;
        this._rect = undefined;
        this._rectChanged = true;
      }

      initialize() {
        this.enableOptionSharing = true;
        super.initialize();
      }

      getMinMax(scale) {
        return {
          min: 0,
          max: scale.axis === "x" ? scale.right - scale.left : scale.bottom - scale.top,
        };
      }

      configure() {
        super.configure();
        const { xScale, yScale } = this.getMeta();
        if (!xScale || !yScale) {
          // configure is called once before `linkScales`, and at that call we don't have any scales linked yet
          return;
        }

        const w = xScale.right - xScale.left;
        const h = yScale.bottom - yScale.top;
        const rect = { x: 0, y: 0, w, h, rtl: !!this.options.rtl, unsorted: !!this.options.unsorted };

        if (rectNotEqual(this._rect, rect)) {
          this._rect = rect;
          this._rectChanged = true;
        }

        if (this._rectChanged) {
          xScale.max = w;
          xScale.configure();
          yScale.max = h;
          yScale.configure();
        }
      }

      update(mode) {
        const dataset = this.getDataset();
        const { data } = this.getMeta();
        const groups = dataset.groups || [];
        const keys = [dataset.key || ""].concat(dataset.sumKeys || []);
        const tree = (dataset.tree = dataset.tree || dataset.data || []);

        if (mode === "reset") {
          // reset is called before 2nd configure and is only called if animations are enabled. So wen need an extra configure call here.
          this.configure();
        }

        if (
          this._rectChanged ||
          arrayNotEqual(this._keys, keys) ||
          arrayNotEqual(this._groups, groups) ||
          this._prevTree !== tree
        ) {
          this._groups = groups.slice();
          this._keys = keys.slice();
          this._prevTree = tree;
          this._rectChanged = false;

          dataset.data = buildData(tree, dataset, this._keys, this._rect);
          // @ts-ignore using private stuff
          this._dataCheck();
          // @ts-ignore using private stuff
          this._resyncElements();
        }

        this.updateElements(data, 0, data.length, mode);
      }

      updateElements(rects, start, count, mode) {
        const reset = mode === "reset";
        const dataset = this.getDataset();
        const firstOpts = (this._rect.options = this.resolveDataElementOptions(start, mode));
        const sharedOptions = this.getSharedOptions(firstOpts);
        const includeOptions = this.includeOptions(mode, sharedOptions);
        const { xScale, yScale } = this.getMeta(this.index);

        for (let i = start; i < start + count; i++) {
          const options = sharedOptions || this.resolveDataElementOptions(i, mode);
          const properties = scaleRect(dataset.data[i], xScale, yScale, options.spacing);
          if (reset) {
            properties.width = 0;
            properties.height = 0;
          }

          if (includeOptions) {
            properties.options = options;
          }
          this.updateElement(rects[i], i, properties, mode);
        }

        this.updateSharedOptions(sharedOptions, mode, firstOpts);
      }

      draw() {
        const { ctx, chartArea } = this.chart;
        const metadata = this.getMeta().data || [];
        const dataset = this.getDataset();
        const data = dataset.data;

        helpers.clipArea(ctx, chartArea);
        for (let i = 0, ilen = metadata.length; i < ilen; ++i) {
          const rect = metadata[i];
          if (!rect.hidden) {
            rect.draw(ctx, data[i]);
          }
        }
        helpers.unclipArea(ctx);
      }
    }

    TreemapController.id = "treemap";

    TreemapController.version = version;

    TreemapController.defaults = {
      dataElementType: "treemap",

      animations: {
        numbers: {
          type: "number",
          properties: ["x", "y", "width", "height"],
        },
      },
    };

    TreemapController.descriptors = {
      _scriptable: true,
      _indexable: false,
    };

    TreemapController.overrides = {
      interaction: {
        mode: "point",
        includeInvisible: true,
        intersect: true,
      },

      hover: {},

      plugins: {
        tooltip: {
          position: "treemap",
          intersect: true,
          callbacks: {
            title(items) {
              if (items.length) {
                const item = items[0];
                return item.dataset.key || "";
              }
              return "";
            },
            label(item) {
              const dataset = item.dataset;
              const dataItem = dataset.data[item.dataIndex];
              const label = dataItem.g || dataItem._data.label || dataset.label;
              return (label ? label + ": " : "") + dataItem.v;
            },
          },
        },
      },
      scales: {
        x: {
          type: "linear",
          alignToPixels: true,
          bounds: "data",
          display: false,
        },
        y: {
          type: "linear",
          alignToPixels: true,
          bounds: "data",
          display: false,
          reverse: true,
        },
      },
    };

    TreemapController.beforeRegister = function () {
      requireVersion("chart.js", "3.8", chart_js.Chart.version);
    };

    TreemapController.afterRegister = function () {
      const tooltipPlugin = chart_js.registry.plugins.get("tooltip");
      if (tooltipPlugin) {
        tooltipPlugin.positioners.treemap = function (active) {
          if (!active.length) {
            return false;
          }

          const item = active[active.length - 1];
          const el = item.element;

          return el.tooltipPosition();
        };
      } else {
        console.warn(
          "Unable to register the treemap positioner because tooltip plugin is not registered"
        );
      }
    };

    TreemapController.afterUnregister = function () {
      const tooltipPlugin = chart_js.registry.plugins.get("tooltip");
      if (tooltipPlugin) {
        delete tooltipPlugin.positioners.treemap;
      }
    };

    chart_js.Chart.register(TreemapController, TreemapElement);

    exports.flatten = flatten;
    exports.getGroupKey = getGroupKey;
    exports.group = group;
    exports.index = index;
    exports.normalizeTreeToArray = normalizeTreeToArray;
    exports.requireVersion = requireVersion;
    exports.sort = sort;
    exports.sum = sum;
  });
