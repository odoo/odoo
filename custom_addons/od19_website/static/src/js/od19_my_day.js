/* Employee portal — "My Day" strip + schedule (lazy JSON, no framework). */
(function () {
    'use strict';

    function escapeHtml(value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function setText(root, field, value) {
        if (value === null || value === undefined || value === '') return;
        var node = root.querySelector('[data-od19-field="' + field + '"]');
        if (node) node.textContent = value;
    }

    function renderSchedule(root, items) {
        var container = root.querySelector('[data-od19-schedule]');
        if (!container) return;
        if (!items || !items.length) {
            container.innerHTML = '<p class="text-muted small mb-0">ไม่มีรายการในสัปดาห์นี้</p>';
            return;
        }
        var html = '';
        items.forEach(function (item) {
            html += '<div class="od19-schedule-item od19-schedule-' + escapeHtml(item.kind) + '">' +
                '<div class="od19-schedule-time">' + escapeHtml(item.time) + '</div>' +
                '<div class="od19-schedule-main">' +
                '<span class="od19-schedule-label">' + escapeHtml(item.label) + '</span>' +
                (item.detail ? '<span class="od19-schedule-detail"> · ' + escapeHtml(item.detail) + '</span>' : '') +
                '</div></div>';
        });
        container.innerHTML = html;
    }

    function render(root, data) {
        if (!data) return;
        var attendance = data.attendance || {};
        if (attendance.available) {
            setText(root, 'attendance',
                'เข้า ' + (attendance.check_in || '—') + ' · ออก ' + (attendance.check_out || '—'));
        }
        if (data.approvals) {
            setText(root, 'approvals', String(data.approvals.pending_count || 0) + ' รายการ');
        }
        if (data.next_booking) {
            setText(root, 'next_booking',
                data.next_booking.start + ' · ' + (data.next_booking.room || ''));
        }
        if (data.leave && data.leave.available) {
            setText(root, 'leave', 'เหลือ ' + data.leave.remaining_display + ' วัน');
        }
        // The schedule panel lives outside #od19-my-day, so resolve it from the document.
        renderSchedule(document, data.schedule);
    }

    function load() {
        var root = document.getElementById('od19-my-day');
        if (!root || root.dataset.loaded) return;
        root.dataset.loaded = '1';
        fetch(root.dataset.od19MeSummary, {
            headers: { Accept: 'application/json' },
            credentials: 'same-origin',
        })
            .then(function (response) {
                if (!response.ok) throw new Error('HTTP ' + response.status);
                return response.json();
            })
            .then(function (data) { render(root, data); })
            .catch(function () { /* keep the placeholders as-is */ });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', load);
    } else {
        load();
    }
})();
