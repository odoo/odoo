/*
@license

dhtmlxGantt v.3.1.0 Stardard
This software is covered by GPL license. You also can obtain Commercial or Enterprise license to use it in non-GPL project - please contact sales@dhtmlx.com. Usage without proper license is prohibited.

(c) Dinamenta, UAB.
*/
function call_tooltip() {
    gantt._tooltip = {}, gantt._tooltip_class = "gantt_tooltip", gantt.config.tooltip_timeout = 30, gantt.config.tooltip_offset_y = 20, gantt.config.tooltip_offset_x = 10, gantt._create_tooltip = function () {
        return this._tooltip_html || (this._tooltip_html = document.createElement("div"), this._tooltip_html.className = gantt._tooltip_class), this._tooltip_html
    }, gantt._is_cursor_under_tooltip = function (t, e) {
        return t.x >= e.pos.x && t.x <= e.pos.x + e.width ? !0 : t.y >= e.pos.y && t.y <= e.pos.y + e.height ? !0 : !1
    }, gantt._show_tooltip = function (t, e) {
        if (!gantt.config.touch || gantt.config.touch_tooltip) {
            var n = this._create_tooltip();
            n.innerHTML = t, gantt.$task_data.appendChild(n);
            var i = n.offsetWidth + 20,
                a = n.offsetHeight + 40,
                s = this.$task.offsetHeight,
                r = this.$task.offsetWidth,
                o = this.getScrollState();
            e.y += o.y;
            var d = {
                x: e.x,
                y: e.y
            };
            e.x += 1 * gantt.config.tooltip_offset_x || 0, e.y += 1 * gantt.config.tooltip_offset_y || 0, e.y = Math.min(Math.max(o.y, e.y), o.y + s - a), e.x = Math.min(Math.max(o.x, e.x), o.x + r - i), gantt._is_cursor_under_tooltip(d, {
                pos: e,
                width: i,
                height: a
            }) && (d.x + i > r + o.x && (e.x = d.x - (i - 20) - (1 * gantt.config.tooltip_offset_x || 0)), d.y + a > s + o.y && (e.y = d.y - (a - 40) - (1 * gantt.config.tooltip_offset_y || 0))), n.style.left = e.x + "px", n.style.top = e.y + "px"
        }
    }, gantt._hide_tooltip = function () {
        this._tooltip_html && this._tooltip_html.parentNode && this._tooltip_html.parentNode.removeChild(this._tooltip_html), this._tooltip_id = 0
    }, gantt._is_tooltip = function (t) {
        var e = t.target || t.srcElement;
        return gantt._is_node_child(e, function (t) {
            return t.className == this._tooltip_class
        })
    }, gantt._is_task_line = function (t) {
        var e = t.target || t.srcElement;
        return gantt._is_node_child(e, function (t) {
            return t == this.$task_data
        })
    }, gantt._is_node_child = function (t, e) {
        for (var n = !1; t && !n;) n = e.call(gantt, t), t = t.parentNode;
        return n
    }, gantt._tooltip_pos = function (t) {
        if (t.pageX || t.pageY) var e = {
            x: t.pageX,
            y: t.pageY
        };
        var n = _isIE ? document.documentElement : document.body,
            e = {
                x: t.clientX + n.scrollLeft - n.clientLeft,
                y: t.clientY + n.scrollTop - n.clientTop
            }, i = gantt._get_position(gantt.$task_data);
        return e.x = e.x - i.x, e.y = e.y - i.y, e
    }, gantt.attachEvent("onMouseMove", function (t, e) {
        if (this.config.tooltip_timeout) {
            document.createEventObject && !document.createEvent && (e = document.createEventObject(e));
            var n = this.config.tooltip_timeout;
            this._tooltip_id && !t && (isNaN(this.config.tooltip_hide_timeout) || (n = this.config.tooltip_hide_timeout)), clearTimeout(gantt._tooltip_ev_timer), gantt._tooltip_ev_timer = setTimeout(function () {
                gantt._init_tooltip(t, e)
            }, n)
        } else gantt._init_tooltip(t, e)
    }), gantt._init_tooltip = function (t, e) {
        if (!this._is_tooltip(e) && (t != this._tooltip_id || this._is_task_line(e))) {
            if (!t) return this._hide_tooltip();
            this._tooltip_id = t;
            var n = this.getTask(t),
                i = this.templates.tooltip_text(n.start_date, n.end_date, n);
            i || this._hide_tooltip(), this._show_tooltip(i, this._tooltip_pos(e))
        }
    }, gantt.attachEvent("onMouseLeave", function (t) {
        gantt._is_tooltip(t) || this._hide_tooltip()
    }), gantt.templates.tooltip_date_format = gantt.date.date_to_str("%Y-%m-%d"), gantt.templates.tooltip_text = function (t, e, n) {
        return "<b>Task:</b> " + n.text + "<br/><b>Start date:</b> " + gantt.templates.tooltip_date_format(t) + "<br/><b>End date:</b> " + gantt.templates.tooltip_date_format(e)
    };
}
call_tooltip();
//# sourceMappingURL=../sources/ext/dhtmlxgantt_tooltip.js.map