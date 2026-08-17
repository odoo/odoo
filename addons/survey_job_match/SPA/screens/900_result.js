/* Closing screen: the match, and the record.

   The ranking is computed in the browser, so it is shown straight away and the
   record is saved in the background. A failed save leaves the result on screen
   with a retry, rather than hiding what the visitor came for. */
JM.registerScreen("result", {
    noBack: true,
    counted: false,

    setup: function () {
        JM.dom.role("result", "retry").addEventListener("click", function () {
            JM.screens.result.save();
        });
    },

    enter: function () {
        JM.screens.result.render();
        JM.screens.result.save();
    },

    render: function () {
        var config = JM.config.result || {};
        var results = JM.scoring.results();
        var match = JM.dom.role("result", "match");

        /* Nothing to rank: no profiles configured, or nothing answered. */
        if (!results.length) {
            JM.dom.show(match, false);
            return;
        }
        JM.dom.show(match, true);

        var best = results[0];
        JM.dom.text(JM.dom.role("result", "intro"),
            config.best_label || "Your best match is");
        JM.dom.text(JM.dom.role("result", "best_name"), best.profile.name);
        JM.dom.text(JM.dom.role("result", "best_percent"),
            best.percentage + "% match");
        JM.dom.role("result", "best_bar").style.width = best.percentage + "%";
        JM.dom.html(JM.dom.role("result", "best_description"),
            best.profile.description_html);

        var cta = JM.dom.role("result", "cta");
        JM.dom.show(cta, !!best.profile.posting_url);
        if (best.profile.posting_url) {
            cta.setAttribute("href", best.profile.posting_url);
            JM.dom.text(cta, config.cta_label || "See the job");
        }

        JM.screens.result.renderRunners(results.slice(1, (config.runners_count || 2) + 1));
    },

    renderRunners: function (runners) {
        var config = JM.config.result || {};
        var box = JM.dom.role("result", "runners");
        var list = JM.dom.role("result", "runners_list");

        JM.dom.show(box, !!runners.length);
        JM.dom.text(JM.dom.role("result", "runners_label"),
            config.runners_label || "Other roles you'd fit");

        list.replaceChildren();
        runners.forEach(function (runner) {
            var row = document.createElement("div");
            row.className = "jm_runner";

            var head = document.createElement("div");
            head.className = "jm_runner_head";
            var name = document.createElement("span");
            name.textContent = runner.profile.name;
            var percent = document.createElement("span");
            percent.className = "jm_runner_percent";
            percent.textContent = runner.percentage + "%";
            head.appendChild(name);
            head.appendChild(percent);

            var meter = document.createElement("div");
            meter.className = "jm_meter jm_meter_small";
            var bar = document.createElement("div");
            bar.className = "jm_meter_bar";
            bar.style.width = runner.percentage + "%";
            meter.appendChild(bar);

            row.appendChild(head);
            row.appendChild(meter);
            list.appendChild(row);
        });
    },

    save: function () {
        var status = JM.dom.role("result", "status");
        var error = JM.dom.role("result", "error");
        var actions = JM.dom.role("result", "actions");

        JM.dom.text(status, "Saving your answers...");
        JM.dom.error(error, "");
        JM.dom.show(actions, false);

        var failed = function (message) {
            JM.dom.text(status, "");
            JM.dom.error(error, message);
            JM.dom.show(actions, true);
        };

        JM.api.save().then(function (result) {
            if (result.id) {
                var suffix = "";
                if (result.mock) {
                    suffix = " (dev preview, nothing was saved)";
                }
                JM.dom.text(status, "Thanks, " + JM.api.visitorName()
                    + "! Your answers are saved." + suffix);
                return;
            }
            failed("Could not save your answers: " + JM.api.errorOf(result));
        }).catch(function (problem) {
            failed("Network error: " + problem.message);
        });
    }
});
