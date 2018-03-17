$(document).ready(function() {
    var useOnComplete = false,
        useEasing = true,
        easingFn = null,
        useGrouping = true,
        options = {
            useEasing: useEasing, // toggle easing
            easingFn: easingFn, // defaults to easeOutExpo, but you can specify your
            // own
            useGrouping: useGrouping, // 1,000,000 vs 1000000
            separator: ',', // character to use as a separator
            decimal: '.', // character to use as a decimal
        };
    var demo, code, data, stars, easingFunctions;
    // create instance
    window.onload = function() {
        // setup CountUp object
        demo = new CountUp('count_2000', 0, 2000, 0, 2, options);
        demo1 = new CountUp('count_1000', 0, 1000, 0, 2, options);
        demo2 = new CountUp('count_188', 0, 188, 0, 2, options);
        demo3 = new CountUp('count_20', 0, 20, 0, 2, options);
        // you could do demo.start() right here but we are getting actual current star
        // count from github api below
        // since it is an asynchronous call, we fire start() in the success fn of the
        // XMLHttpRequest object
        demo.start();
        demo1.start();
        demo2.start();
        demo3.start();
    };
});
