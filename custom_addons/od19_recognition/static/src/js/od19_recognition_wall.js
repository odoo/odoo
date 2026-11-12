/* Employee portal — Team Wall strip (lazy JSON). */
(function () {
    'use strict';

    function esc(value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function renderFeed(container, feed) {
        if (!feed || !feed.length) {
            container.innerHTML = '<p class="text-muted small mb-0">ยังไม่มี Kudos</p>';
            return;
        }
        container.innerHTML = feed.map(function (item) {
            return '<div class="od19-kudos-item mb-2">' +
                '<div class="d-flex align-items-center gap-2">' +
                '<span class="od19-kudos-badge" style="background:' + esc(item.badge_color) + '">' +
                '<i class="fa ' + esc(item.badge_icon) + '"></i></span>' +
                '<strong>' + esc(item.author) + '</strong>' +
                '<i class="fa fa-arrow-right text-muted" style="font-size:0.7rem;"></i>' +
                '<strong>' + esc(item.recipient) + '</strong>' +
                '<small class="text-muted ms-auto">' + esc(item.date) + '</small></div>' +
                '<div class="od19-kudos-msg">' + esc(item.message) + '</div></div>';
        }).join('');
    }

    function renderCelebrations(container, celebrations) {
        if (!container || !celebrations) return;
        var parts = [];
        (celebrations.birthdays || []).forEach(function (b) {
            parts.push('<span class="od19-celebration-pill"><i class="fa fa-birthday-cake me-1" style="color:#e91e63;"></i>' + esc(b.name) + '</span>');
        });
        (celebrations.anniversaries || []).forEach(function (a) {
            parts.push('<span class="od19-celebration-pill"><i class="fa fa-trophy me-1" style="color:#f39200;"></i>' + esc(a.name) + ' ' + esc(a.years) + ' ปี</span>');
        });
        if (parts.length) {
            container.innerHTML = '<div class="od19-celebration-title">เดือนนี้</div>' + parts.join('');
            container.classList.remove('d-none');
        }
    }

    function load() {
        var root = document.querySelector('.od19-team-wall');
        if (!root || root.dataset.loaded) return;
        root.dataset.loaded = '1';
        fetch(root.dataset.od19RecognitionSummary, {
            headers: { Accept: 'application/json' },
            credentials: 'same-origin',
        })
            .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
            .then(function (data) {
                renderFeed(root.querySelector('.od19-kudos-feed'), data.feed);
                renderCelebrations(root.querySelector('.od19-celebrations'), data.celebrations);
            })
            .catch(function () { /* keep placeholder */ });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', load);
    } else {
        load();
    }
})();
