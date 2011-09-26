(function ($) {
    "use strict";
    $.extend($.Deferred, {
        queue: function () {
            var queueDeferred = $.Deferred();
            var promises = 0;

            function resolve() {
                if (--promises > 0) {
                    return;
                }
                setTimeout($.proxy(queueDeferred, 'resolve'), 0);
            }

            var promise = $.extend(queueDeferred.promise(), {
                push: function () {
                    if (this.isResolved() || this.isRejected()) {
                        throw new Error("Can not add promises to a resolved "
                                        + "or rejected promise queue");
                    }

                    promises += 1;
                    $.when.apply(null, arguments).then(
                        resolve, $.proxy(queueDeferred, 'reject'));
                    return this;
                }
            });
            if (arguments.length) {
                promise.push.apply(promise, arguments);
            }
            return promise;
        }
    });
})(jQuery)
