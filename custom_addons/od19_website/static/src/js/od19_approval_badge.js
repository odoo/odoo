/** Auto-Info Employee Portal — the lazy "pending approvals" badge. */
(function () {
    'use strict';

    function fill(holder, payload) {
        if (!payload || !payload.pending_count) {
            return;
        }
        var count = holder.querySelector('.od19-approval-count');
        if (count) {
            count.textContent = payload.pending_count;
        }
        if (payload.max_age_days) {
            var maxAge = holder.querySelector('.od19-approval-max-age');
            var ageWrap = holder.querySelector('.od19-approval-age');
            if (maxAge) {
                maxAge.textContent = payload.max_age_days;
            }
            if (ageWrap) {
                ageWrap.classList.remove('d-none');
            }
        }
        holder.classList.remove('d-none');
    }

    function load(holder) {
        if (holder.dataset.loaded) {
            return;
        }
        holder.dataset.loaded = '1';
        fetch(holder.dataset.od19ApprovalSummary, {
            headers: { Accept: 'application/json' },
            credentials: 'same-origin',
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }
                return response.json();
            })
            .then(function (payload) {
                fill(holder, payload);
            })
            .catch(function () {
                // The card and its link keep working; only the badge is lost.
                holder.classList.add('d-none');
            });
    }

    function init() {
        document.querySelectorAll('[data-od19-approval-summary]').forEach(load);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
