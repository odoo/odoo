/* Scoring: turning the answers into a ranked list of job profiles.

   The rules are the reference implementation's, described in README.md 2.2:

     - only profiles weighted somewhere in the questionnaire take part
     - every picked answer adds its points to each profile it weights, and
       points may be negative
     - the percentage is relative to what was achievable, not to other
       visitors: per question, the best possible contribution toward a profile
       is the sum of its positive weights for a multiple-choice question (you
       could tick them all) or the single best one otherwise
     - the percentage is clamped into 0-100, and a profile whose ceiling is zero
       scores 0
     - results rank by score first, then by percentage

   Elimination is not applied yet. The data carries it, and README.md 5 spells
   out what that costs. */
JM.scoring = {
    profiles: function () {
        return JM.data.profiles || [];
    },

    choiceQuestions: function () {
        return (JM.data.questions || []).filter(function (question) {
            return question.type !== "text";
        });
    },

    /* The choice objects the visitor actually picked. */
    picked: function () {
        var out = [];
        JM.scoring.choiceQuestions().forEach(function (question) {
            var chosen = JM.state.answers[question.id];
            if (chosen) {
                out.push(chosen);
            }
        });
        return out;
    },

    /* A profile takes part as soon as any answer weights it, one way or another. */
    participating: function () {
        var seen = {};
        JM.scoring.choiceQuestions().forEach(function (question) {
            question.choices.forEach(function (choice) {
                Object.keys(choice.points || {}).forEach(function (id) {
                    seen[id] = true;
                });
                (choice.eliminates || []).forEach(function (id) {
                    seen[id] = true;
                });
            });
        });
        return JM.scoring.profiles().filter(function (profile) {
            return seen[profile.id];
        });
    },

    scores: function () {
        var totals = {};
        JM.scoring.picked().forEach(function (choice) {
            Object.keys(choice.points || {}).forEach(function (id) {
                totals[id] = (totals[id] || 0) + choice.points[id];
            });
        });
        return totals;
    },

    /* Best obtainable total per profile, question by question. */
    ceilings: function () {
        var ceilings = {};
        JM.scoring.choiceQuestions().forEach(function (question) {
            var best = {};
            question.choices.forEach(function (choice) {
                Object.keys(choice.points || {}).forEach(function (id) {
                    var value = choice.points[id];
                    if (value > 0) {
                        best[id] = (best[id] || []).concat([value]);
                    }
                });
            });
            Object.keys(best).forEach(function (id) {
                var positives = best[id];
                var contribution = Math.max.apply(null, positives);
                if (question.type === "multiple_choice") {
                    contribution = positives.reduce(function (a, b) {
                        return a + b;
                    }, 0);
                }
                ceilings[id] = (ceilings[id] || 0) + contribution;
            });
        });
        return ceilings;
    },

    /* [{profile, score, max, percentage}], best first. */
    results: function () {
        var scores = JM.scoring.scores();
        var ceilings = JM.scoring.ceilings();
        var results = JM.scoring.participating().map(function (profile) {
            var score = scores[profile.id] || 0;
            var maximum = ceilings[profile.id] || 0;
            var percentage = 0;
            if (maximum > 0) {
                percentage = Math.round(100 * score / maximum);
            }
            return {
                profile: profile,
                score: score,
                max: maximum,
                percentage: Math.max(0, Math.min(100, percentage))
            };
        });
        results.sort(function (a, b) {
            if (b.score !== a.score) {
                return b.score - a.score;
            }
            return b.percentage - a.percentage;
        });
        return results;
    }
};
