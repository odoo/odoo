/* Transport: turning a finished run into a record.

   Writes go to the website module's public form endpoint, which creates the
   record as superuser -- that is what lets an anonymous visitor save anything.
   It always answers HTTP 200 and reports failure inside the JSON body, so
   callers must branch on the body rather than the status code.

   Prerequisites on the target database are configuration, not code: the model
   must be allowed in forms and every field in field_map, plus note_field, must
   be un-blacklisted. See README.md section 3.2. */
JM.api = {
    endpoint: function () {
        return "/website/form/" + JM.config.model;
    },

    /* question id -> model field, from data/config.json. */
    fieldMap: function () {
        return JM.config.field_map || {};
    },

    visitorName: function () {
        var map = JM.api.fieldMap();
        var answer = "";
        Object.keys(map).forEach(function (questionId) {
            if (map[questionId] === JM.config.name_field) {
                answer = JM.state.answers[questionId] || answer;
            }
        });
        return answer;
    },

    post: function (values) {
        if (JM.config.mock) {
            return JM.api.mock(values);
        }
        var body = new FormData();
        /* Only verified for authenticated sessions, i.e. you previewing while
           logged in. Anonymous visitors do not need it, but sending it always
           is what keeps your own preview from failing. */
        body.append("csrf_token", (window.odoo || {}).csrf_token || "");
        Object.keys(values).forEach(function (field) {
            body.append(field, values[field]);
        });
        return fetch(JM.api.endpoint(), {method: "POST", body: body})
            .then(function (response) {
                return response.json();
            });
    },

    /* Dev preview only: pretend the write succeeded. */
    mock: function (values) {
        return new Promise(function (resolve) {
            window.setTimeout(function () {
                window.console.log("[JM] mock submit", values);
                resolve({id: 4242, mock: true});
            }, 400);
        });
    },

    /* Plain-text transcript of the run, stored in the record's note field: the
       answers as given, then the ranking, so a recruiter reading the contact
       sees both what was said and what it produced. */
    transcript: function () {
        var lines = [];
        (JM.data.questions || []).forEach(function (question) {
            var answer = JM.state.answers[question.id];
            if (!answer) {
                return;
            }
            lines.push(question.title);
            /* Choice answers are objects, text answers are plain strings. */
            lines.push(answer.label || answer);
            lines.push("");
        });

        var results = JM.scoring.results();
        if (results.length) {
            lines.push("Best match: " + results[0].profile.name
                + " (" + results[0].percentage + "%)");
            var runners = results.slice(1, 3).map(function (runner) {
                return runner.profile.name + " (" + runner.percentage + "%)";
            });
            if (runners.length) {
                lines.push("Runners-up: " + runners.join(", "));
            }
        }
        return lines.join("\n");
    },

    save: function () {
        var values = {};
        var map = JM.api.fieldMap();
        Object.keys(map).forEach(function (questionId) {
            var answer = JM.state.answers[questionId];
            if (answer) {
                values[map[questionId]] = answer.label || answer;
            }
        });
        values[JM.config.note_field] = JM.api.transcript();
        return JM.api.post(values);
    },

    /* Readable reason out of an endpoint failure body. */
    errorOf: function (result) {
        if (result) {
            if (result.error) {
                return result.error;
            }
            if (result.error_fields) {
                return result.error_fields.join(", ");
            }
        }
        return "the server rejected the values";
    }
};
