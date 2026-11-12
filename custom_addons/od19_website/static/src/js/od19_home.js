/** Auto-Info homepage — animated statistic counters (offline, no libraries). */
(function () {
    'use strict';

    var REDUCED = window.matchMedia
        && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function finalise(el) {
        var target = parseFloat(el.getAttribute('data-od19-count'));
        var suffix = el.getAttribute('data-od19-suffix') || '';
        if (!isNaN(target)) {
            el.textContent = target + suffix;
        }
    }

    function countUp(el) {
        var target = parseFloat(el.getAttribute('data-od19-count'));
        var suffix = el.getAttribute('data-od19-suffix') || '';
        if (isNaN(target)) {
            return;
        }
        var duration = 1400;
        var start = null;

        function frame(ts) {
            if (start === null) {
                start = ts;
            }
            var progress = Math.min((ts - start) / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(target * eased) + suffix;
            if (progress < 1) {
                window.requestAnimationFrame(frame);
            } else {
                finalise(el);
            }
        }
        window.requestAnimationFrame(frame);
    }

    function init() {
        var numbers = document.querySelectorAll('.od19-stat-number[data-od19-count]');
        if (!numbers.length) {
            return;
        }

        if (REDUCED || !('IntersectionObserver' in window)) {
            numbers.forEach(finalise);
            return;
        }

        // Start each counter at zero so the count-up is the first thing seen,
        // then animate when the stats band scrolls into view.
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    countUp(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.4 });

        numbers.forEach(function (el) {
            el.textContent = '0' + (el.getAttribute('data-od19-suffix') || '');
            observer.observe(el);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
